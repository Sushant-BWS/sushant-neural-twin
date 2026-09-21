"""Repository-backed long-term memory service."""

from datetime import datetime
from typing import Any

from backend.memory.base import (
	InMemoryMemoryRepository,
	MemoryRecord,
	MemoryRepository,
)


class LongTermMemory:
	"""Manage durable memory records behind a replaceable repository."""

	def __init__(self, repository: MemoryRepository | None = None) -> None:
		self.repository = repository or InMemoryMemoryRepository()

	def remember(
		self,
		content: str,
		source: str,
		confidence: float,
		metadata: dict[str, Any] | None = None,
		created_at: datetime | None = None,
	) -> MemoryRecord:
		"""Store a traceable long-term memory."""

		record = MemoryRecord(
			content=content,
			source=source,
			confidence=confidence,
			metadata=dict(metadata or {}),
			**({"created_at": created_at} if created_at else {}),
		)
		return self.repository.add(record)

	def get(self, record_id: str) -> MemoryRecord | None:
		"""Return a long-term memory by identifier."""

		return self.repository.get(record_id)

	def records(self, limit: int | None = None) -> list[MemoryRecord]:
		"""Return long-term memories from newest to oldest."""

		return self.repository.list(limit)

	def clear(self) -> None:
		"""Clear all long-term memories."""

		self.repository.clear()

	def count(self) -> int:
		"""Return the number of long-term memories."""

		return self.repository.count()
