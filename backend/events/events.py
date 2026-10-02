"""Simple event dataclasses for workflow orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class UserMessageReceived(Event):
    event_type: str = "user_message_received"


@dataclass
class MemoryCreated(Event):
    event_type: str = "memory_created"


@dataclass
class MemoryUpdated(Event):
    event_type: str = "memory_updated"


@dataclass
class KnowledgeIngested(Event):
    event_type: str = "knowledge_ingested"


@dataclass
class AnswerGenerated(Event):
    event_type: str = "answer_generated"


@dataclass
class ClaimVerified(Event):
    event_type: str = "claim_verified"


@dataclass
class VoiceGenerationStarted(Event):
    event_type: str = "voice_generation_started"


@dataclass
class VoiceGenerationCompleted(Event):
    event_type: str = "voice_generation_completed"
