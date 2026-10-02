"""Conversation manager for tracking sessions and turn summaries."""

from __future__ import annotations

from backend.conversation.context import ConversationContext
from backend.conversation.session import ConversationSession


class ConversationManager:
    """Keep conversations trimmed to the current topic and relevant entities."""

    def __init__(self) -> None:
        self._sessions: dict[str, ConversationSession] = {}

    def create_session(self, session_id: str) -> ConversationSession:
        session = ConversationSession(session_id=session_id)
        self._sessions[session_id] = session
        return session

    def record_turn(self, session_id: str, question: str, answer: str) -> dict[str, object]:
        session = self._sessions.setdefault(session_id, ConversationSession(session_id=session_id))
        session.conversation_history.append(question)
        session.conversation_history.append(answer)
        return {"session_id": session_id, "history": session.conversation_history}

    def context(self, session_id: str) -> ConversationContext:
        session = self._sessions.get(session_id)
        if session is None:
            session = self.create_session(session_id)
        return ConversationContext(session_id=session_id, history=session.conversation_history, active_topic=session.active_topic, entities=session.entities)
