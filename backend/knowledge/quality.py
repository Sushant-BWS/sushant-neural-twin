"""Knowledge quality checks and evidence validation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class QualityResult:
    passed: bool
    score: float
    notes: list[str] | None = None


class KnowledgeQuality:
    """Simple heuristics to keep retrieval results evidence-aware and safe."""

    @staticmethod
    def validate(source: str, content: str, metadata: dict[str, Any] | None = None) -> QualityResult:
        metadata = metadata or {}
        score = 0.0
        notes: list[str] = []

        if source:
            score += 0.25
        if content and len(content.strip()) > 12:
            score += 0.35
        if metadata.get("confidence") is not None:
            score += 0.2
        if metadata.get("source_type") in {"resume", "project", "experience", "thought"}:
            score += 0.2

        passed = score >= 0.6
        if not passed:
            notes.append("Knowledge item is below the quality threshold.")
        else:
            notes.append("Knowledge item looks usable for retrieval.")

        return QualityResult(passed=passed, score=round(score, 2), notes=notes)
