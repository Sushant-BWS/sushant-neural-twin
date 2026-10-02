"""Chat orchestration service."""

from __future__ import annotations

from backend.ai.cognition.cognitive_engine import CognitiveEngine


class ChatService:
    """Coordinate user questions and cognitive processing."""

    def __init__(self, engine: CognitiveEngine | None = None) -> None:
        self.engine = engine or CognitiveEngine()

    def answer(self, question: str, history: list[str] | None = None) -> dict[str, object]:
        return self.engine.process(question, history=history or [])
