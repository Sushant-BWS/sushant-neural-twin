"""Builds compact, task-appropriate context for the reasoning pipeline."""

from __future__ import annotations

from backend.ai.cognition.schemas import InteractionContext


class ContextBuilder:
    """Assemble minimal context with a stable interface for downstream reasoning."""

    def build(self, question: str, intent: str, evidence: list | None = None, history: list[str] | None = None) -> InteractionContext:
        return InteractionContext(
            question=question,
            intent=intent,
            entities=[],
            conversation_history=history or [],
            memory_summary="",
            evidence=evidence or [],
            constraints={},
        )
