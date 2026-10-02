"""Semantic memory for persistent, fact-like knowledge tied to entities."""

from __future__ import annotations

from backend.memory.memory_schemas import SemanticMemory


class SemanticMemoryStore:
    """Simple in-memory semantic memory storage for local-first use."""

    def __init__(self) -> None:
        self._records: list[SemanticMemory] = []

    def add(self, fact: str, subject: str, confidence: float = 0.5, source: str = "conversation", source_type: str = "document") -> SemanticMemory:
        record = SemanticMemory(
            fact=fact,
            subject=subject,
            confidence=confidence,
            source=source,
            source_type=source_type,
        )
        self._records.append(record)
        return record

    def list(self) -> list[SemanticMemory]:
        return list(self._records)

    def query(self, subject: str | None = None) -> list[SemanticMemory]:
        if subject is None:
            return list(self._records)
        return [record for record in self._records if record.subject.lower() == subject.lower()]
