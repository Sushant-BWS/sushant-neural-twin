"""Cognitive orchestration service."""

from __future__ import annotations

from backend.ai.cognition.cognitive_engine import CognitiveEngine


class CognitionService:
    def __init__(self, engine: CognitiveEngine | None = None) -> None:
        self.engine = engine or CognitiveEngine()

    def process(self, question: str, evidence: list | None = None) -> dict[str, object]:
        return self.engine.process(question, evidence=evidence or [])
