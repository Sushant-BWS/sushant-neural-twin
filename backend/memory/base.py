"""Shared memory records and repository interfaces."""

from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class MemoryRecord(BaseModel):
    """A traceable memory item with provenance and confidence metadata."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    id: str = Field(default_factory=lambda: uuid4().hex)
    content: str = Field(min_length=1)
    source: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class MemoryRepository(Protocol):
    """Repository contract shared by all memory services."""

    def add(self, record: MemoryRecord) -> MemoryRecord:
        """Store a record and return the stored value."""
        ...

    def get(self, record_id: str) -> MemoryRecord | None:
        """Return a record by identifier when it exists."""
        ...

    def list(self, limit: int | None = None) -> list[MemoryRecord]:
        """Return records ordered from newest to oldest."""
        ...

    def delete(self, record_id: str) -> bool:
        """Delete a record and report whether it existed."""
        ...

    def clear(self) -> None:
        """Remove all records from the repository."""
        ...

    def count(self) -> int:
        """Return the number of stored records."""
        ...


class InMemoryMemoryRepository:
    """Development repository with no persistence or external services."""

    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}
        self._sequence: dict[str, int] = {}
        self._next_sequence = 0

    def add(self, record: MemoryRecord) -> MemoryRecord:
        """Store a record by ID, replacing an existing record with that ID."""

        now = datetime.now(timezone.utc)
        stored = record.model_copy(update={"updated_at": now})
        self._records[stored.id] = stored
        self._sequence[stored.id] = self._next_sequence
        self._next_sequence += 1
        return stored

    def add_many(self, records: Iterable[MemoryRecord]) -> int:
        """Store multiple records and return the number accepted."""

        accepted = 0
        for record in records:
            self.add(record)
            accepted += 1
        return accepted

    def get(self, record_id: str) -> MemoryRecord | None:
        """Return a record by identifier when it exists."""

        return self._records.get(record_id)

    def list(self, limit: int | None = None) -> list[MemoryRecord]:
        """Return records ordered from newest to oldest."""

        records = sorted(
            self._records.values(),
            key=lambda record: (record.created_at, self._sequence[record.id]),
            reverse=True,
        )
        return records if limit is None else records[:limit]

    def delete(self, record_id: str) -> bool:
        """Delete a record and report whether it existed."""

        existed = self._records.pop(record_id, None) is not None
        self._sequence.pop(record_id, None)
        return existed

    def clear(self) -> None:
        """Remove all records from the repository."""

        self._records.clear()
        self._sequence.clear()
        self._next_sequence = 0

    def count(self) -> int:
        """Return the number of stored records."""

        return len(self._records)
