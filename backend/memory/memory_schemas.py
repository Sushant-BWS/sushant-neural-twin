"""Schemas for working, semantic, and consolidated memory records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class WorkingMemory:
    """Current task state for the active conversation."""

    conversation: list[str] = field(default_factory=list)
    current_question: str = ""
    current_entities: list[str] = field(default_factory=list)
    recent_answers: list[str] = field(default_factory=list)
    active_task: str = ""
    active_context: dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class SemanticMemory:
    """Persistent facts that can be retrieved by topic or entity."""

    fact: str
    subject: str
    confidence: float = 0.5
    source: str = "conversation"
    source_type: str = "document"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MemoryCandidate:
    """A candidate memory selected for consolidation."""

    memory_type: str
    subject: str
    content: str
    importance: float = 0.0
    relevance: float = 0.0
    recency: float = 0.0
    confidence: float = 0.0
    source_reliability: float = 0.5
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "conversation"
    metadata: dict[str, Any] = field(default_factory=dict)
