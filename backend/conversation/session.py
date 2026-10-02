"""A single conversation session model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ConversationSession:
    session_id: str
    conversation_history: list[str] = field(default_factory=list)
    active_topic: str = "general"
    entities: list[str] = field(default_factory=list)
    memory_candidates: list[str] = field(default_factory=list)
