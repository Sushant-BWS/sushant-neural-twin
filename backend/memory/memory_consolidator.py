"""Consolidates important interaction data into persistent memory."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.memory.memory_decay import MemoryDecay
from backend.memory.memory_relevance import MemoryRelevance
from backend.memory.memory_schemas import MemoryCandidate, SemanticMemory


class MemoryConsolidator:
    """Score memory candidates and persist only important items."""

    def __init__(self, threshold: float = 0.62) -> None:
        self.threshold = threshold

    def score(self, candidate: MemoryCandidate) -> float:
        recency = MemoryDecay.from_timestamp(candidate.timestamp)
        relevance = MemoryRelevance.score(
            recency=recency,
            frequency=0.5,
            importance=candidate.importance,
            relevance=candidate.relevance,
            confidence=candidate.confidence,
        )
        return max(0.0, min(1.0, relevance))

    def should_persist(self, candidate: MemoryCandidate) -> bool:
        return self.score(candidate) >= self.threshold

    def consolidate(self, candidate: MemoryCandidate) -> SemanticMemory | None:
        if not self.should_persist(candidate):
            return None
        return SemanticMemory(
            fact=candidate.content,
            subject=candidate.subject,
            confidence=max(0.0, min(1.0, candidate.confidence)),
            source=candidate.source,
            source_type="conversation",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            metadata={"memory_type": candidate.memory_type, **candidate.metadata},
        )
