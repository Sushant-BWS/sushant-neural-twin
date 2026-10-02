"""Core schemas for the cognitive planning and reasoning pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntentType(str, Enum):
    """Supported user intents."""

    GENERAL = "general"
    PROFILE = "profile"
    SKILL = "skill"
    PROJECT = "project"
    EDUCATION = "education"
    CAREER = "career"
    EXPERIENCE = "experience"
    CERTIFICATION = "certification"
    THOUGHT = "thought"
    RECRUITER = "recruiter"


class RetrievalMode(str, Enum):
    """Supported retrieval modes."""

    KEYWORD = "keyword"
    VECTOR = "vector"
    HYBRID = "hybrid"
    METADATA = "metadata"


class ConfidenceLevel(str, Enum):
    """Confidence output values."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class EvidenceRecord:
    """Evidence for a fact or claim."""

    source: str
    content: str
    score: float = 0.0
    reliability: float = 0.5
    recency: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class QueryPlan:
    """Structured planning output for a user query."""

    intent: str
    sources: list[str]
    retrieval_mode: str = RetrievalMode.HYBRID.value
    memory_required: bool = True
    reasoning_required: bool = True
    llm_required: bool = True
    voice_required: bool = False
    verification_required: bool = True
    required_sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "sources": self.sources,
            "retrieval_mode": self.retrieval_mode,
            "memory_required": self.memory_required,
            "reasoning_required": self.reasoning_required,
            "llm_required": self.llm_required,
            "voice_required": self.voice_required,
            "verification_required": self.verification_required,
            "required_sources": self.required_sources or self.sources,
        }


@dataclass(slots=True)
class InteractionContext:
    """Minimal context object passed during orchestration."""

    question: str
    intent: str = "general"
    entities: list[str] = field(default_factory=list)
    conversation_history: list[str] = field(default_factory=list)
    memory_summary: str = ""
    evidence: list[EvidenceRecord] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
