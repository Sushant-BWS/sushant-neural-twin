"""Timestamped episodic memory service."""

from datetime import datetime, timezone
from typing import Any

from pydantic import Field

from backend.memory.base import (
	InMemoryMemoryRepository,
	MemoryRecord,
	MemoryRepository,
)


class EpisodicMemoryRecord(MemoryRecord):
	"""A memory tied to the time an event occurred."""

	occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EpisodicMemory:
	"""Manage source-aware events independently from other memory types."""

	def __init__(self, repository: MemoryRepository | None = None) -> None:
		self.repository = repository or InMemoryMemoryRepository()

	def record_event(
		self,
		content: str,
		source: str,
		confidence: float,
		occurred_at: datetime | None = None,
		metadata: dict[str, Any] | None = None,
	) -> EpisodicMemoryRecord:
		"""Record an event with its occurrence timestamp."""

		record = EpisodicMemoryRecord(
			content=content,
			source=source,
			confidence=confidence,
			occurred_at=occurred_at or datetime.now(timezone.utc),
			metadata=dict(metadata or {}),
		)
		stored = self.repository.add(record)
		return EpisodicMemoryRecord.model_validate(stored.model_dump())

	def get(self, record_id: str) -> EpisodicMemoryRecord | None:
		"""Return an episodic memory by identifier."""

		record = self.repository.get(record_id)
		return EpisodicMemoryRecord.model_validate(record.model_dump()) if record else None

	def events(self, limit: int | None = None) -> list[EpisodicMemoryRecord]:
		"""Return episodic memories from newest creation time to oldest."""

		return [
			EpisodicMemoryRecord.model_validate(record.model_dump())
			for record in self.repository.list(limit)
		]

	def clear(self) -> None:
		"""Clear all episodic memories."""

		self.repository.clear()

	def count(self) -> int:
		"""Return the number of episodic memories."""

		return self.repository.count()
