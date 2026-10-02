"""Conversation summarization and session service."""

from __future__ import annotations

from backend.conversation.manager import ConversationManager


class ConversationService:
    def __init__(self, manager: ConversationManager | None = None) -> None:
        self.manager = manager or ConversationManager()

    def add_turn(self, session_id: str, question: str, answer: str) -> dict[str, object]:
        return self.manager.record_turn(session_id, question, answer)
