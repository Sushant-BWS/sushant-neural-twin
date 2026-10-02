"""Public response schema for user-facing answers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class VoiceStatus:
    available: bool = True


@dataclass(slots=True)
class ResponseContract:
    answer: str
    confidence: str = "HIGH"
    reasoning_summary: str = ""
    evidence: list[dict[str, Any]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    voice: VoiceStatus = field(default_factory=VoiceStatus)

    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "confidence": self.confidence,
            "reasoning_summary": self.reasoning_summary,
            "evidence": self.evidence,
            "sources": self.sources,
            "voice": {"available": self.voice.available},
        }
