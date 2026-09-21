"""Replaceable interfaces for storing normalized knowledge documents."""

from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class KnowledgeDocument(BaseModel):
    """A normalized document with source metadata."""

    id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class KnowledgeIndex(Protocol):
    """Interface for a future persistent or searchable knowledge index."""

    def add(self, documents: Iterable[KnowledgeDocument]) -> int:
        """Store documents and return the number accepted."""
        ...

    def count(self) -> int:
        """Return the number of indexed documents."""
        ...

    def documents(self) -> list[KnowledgeDocument]:
        """Return indexed documents in insertion order."""
        ...


class InMemoryKnowledgeIndex:
    """Small local index implementation for development and testing."""

    def __init__(self) -> None:
        self._documents: dict[str, KnowledgeDocument] = {}

    def add(self, documents: Iterable[KnowledgeDocument]) -> int:
        """Store documents by stable identifier, replacing duplicate IDs."""

        accepted = 0
        for document in documents:
            self._documents[document.id] = document
            accepted += 1
        return accepted

    def count(self) -> int:
        """Return the number of uniquely indexed documents."""

        return len(self._documents)

    def documents(self) -> list[KnowledgeDocument]:
        """Return indexed documents in insertion order."""

        return list(self._documents.values())
