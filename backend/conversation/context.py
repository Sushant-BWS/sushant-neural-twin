"""Conversation context model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ConversationContext:
    session_id: str
    history: list[str] = field(default_factory=list)
    active_topic: str = "general"
    entities: list[str] = field(default_factory=list)
