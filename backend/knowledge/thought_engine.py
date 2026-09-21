"""Evidence-aware engine for explicitly documented thought patterns."""

from collections.abc import Iterable
from enum import StrEnum
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.knowledge.schemas import Thought
from backend.memory.thought_memory import ThoughtMemory, ThoughtMemoryRecord


class EvidenceType(StrEnum):
    """Allowed evidence categories for a personal knowledge statement."""

    FACT = "FACT"
    EXPERIENCE = "EXPERIENCE"
    DOCUMENTED_THOUGHT = "DOCUMENTED_THOUGHT"
    INFERENCE = "INFERENCE"
    UNKNOWN = "UNKNOWN"


class ThoughtAssessment(BaseModel):
    """Transparent classification result for one statement."""

    model_config = ConfigDict(frozen=True)

    evidence_type: EvidenceType
    supported: bool
    rationale: str
    evidence: list[str] = Field(default_factory=list)


class ThoughtSearchResult(BaseModel):
    """A documented thought and its lexical relevance score."""

    thought: ThoughtMemoryRecord
    score: float = Field(ge=0, le=1)


class ThoughtEngine:
    """Store and retrieve explicitly documented thought patterns.

    The engine never creates a thought from a query and never upgrades an
    inference into a fact. Classification is supplied by the data owner or
    remains UNKNOWN when evidence is insufficient.
    """

    _token_pattern = re.compile(r"[a-z0-9]+")

    def __init__(self, memory: ThoughtMemory | None = None) -> None:
        self.memory = memory or ThoughtMemory()

    def add_documented_thought(self, thought: Thought) -> ThoughtMemoryRecord:
        """Store a thought from an explicit structured knowledge record."""

        if not thought.topic or not thought.statement or not thought.source:
            raise ValueError("topic, statement, and source are required")
        return self.memory.remember(
            topic=thought.topic,
            statement=thought.statement,
            source=thought.source,
            confidence=thought.confidence if thought.confidence is not None else 0.0,
            evidence=thought.evidence,
            metadata={"context": thought.context},
            created_at=thought.created_at,
        )

    def assess(
        self,
        evidence_type: EvidenceType,
        evidence: Iterable[str] | None = None,
    ) -> ThoughtAssessment:
        """Assess support without inferring a classification."""

        references = [reference.strip() for reference in evidence or [] if reference.strip()]
        if evidence_type is EvidenceType.UNKNOWN:
            return ThoughtAssessment(
                evidence_type=evidence_type,
                supported=False,
                rationale="No verified evidence classification was provided.",
                evidence=references,
            )
        if evidence_type is EvidenceType.INFERENCE:
            return ThoughtAssessment(
                evidence_type=evidence_type,
                supported=bool(references),
                rationale="Inference is kept distinct from verified personal knowledge.",
                evidence=references,
            )
        return ThoughtAssessment(
            evidence_type=evidence_type,
            supported=bool(references) or evidence_type is EvidenceType.DOCUMENTED_THOUGHT,
            rationale="Classification is accepted only as explicitly supplied by the data owner.",
            evidence=references,
        )

    def search(self, query: str, limit: int = 5) -> list[ThoughtSearchResult]:
        """Retrieve documented thoughts by transparent token overlap."""

        if limit < 1:
            raise ValueError("limit must be at least 1")
        query_tokens = set(self._token_pattern.findall(query.lower()))
        if not query_tokens:
            return []

        results: list[ThoughtSearchResult] = []
        for thought in self.memory.thoughts():
            thought_tokens = set(
                self._token_pattern.findall(
                    f"{thought.topic} {thought.content} {thought.metadata.get('context', '')}".lower()
                )
            )
            score = len(query_tokens & thought_tokens) / len(query_tokens)
            if score:
                results.append(ThoughtSearchResult(thought=thought, score=score))

        results.sort(key=lambda result: (-result.score, result.thought.id))
        return results[:limit]

    def thoughts(self, limit: int | None = None) -> list[ThoughtMemoryRecord]:
        """Return stored documented thoughts from newest to oldest."""

        return self.memory.thoughts(limit)

    def count(self) -> int:
        """Return the number of documented thoughts."""

        return self.memory.count()
