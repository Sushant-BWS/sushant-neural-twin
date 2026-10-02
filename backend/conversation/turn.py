"""Single user-assistant turn object."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ConversationTurn:
    user_question: str
    assistant_answer: str
    memory_candidates: list[str] | None = None
