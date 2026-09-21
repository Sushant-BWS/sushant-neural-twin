"""Bounded short-term memory service."""

from datetime import datetime
from typing import Any

from backend.memory.base import (
	InMemoryMemoryRepository,
	MemoryRecord,
	MemoryRepository,
)


class ShortTermMemory:
	"""Manage recent memories with a configurable item limit."""

	def __init__(
		self,
		repository: MemoryRepository | None = None,
		max_items: int = 20,
	) -> None:
		if max_items < 1:
			raise ValueError("max_items must be at least 1")
		self.repository = repository or InMemoryMemoryRepository()
		self.max_items = max_items

	def add(
		self,
		content: str,
		source: str,
		confidence: float,
		metadata: dict[str, Any] | None = None,
		created_at: datetime | None = None,
	) -> MemoryRecord:
		"""Add a recent memory and evict the oldest excess records."""

		record = MemoryRecord(
			content=content,
			source=source,
			confidence=confidence,
			metadata=dict(metadata or {}),
			**({"created_at": created_at} if created_at else {}),
		)
		stored = self.repository.add(record)
		self._evict_excess()
		return stored

	def get(self, record_id: str) -> MemoryRecord | None:
		"""Return a recent memory by identifier."""

		return self.repository.get(record_id)

	def recent(self, limit: int | None = None) -> list[MemoryRecord]:
		"""Return recent memories from newest to oldest."""

		return self.repository.list(limit)

	def clear(self) -> None:
		"""Clear all short-term memories."""

		self.repository.clear()

	def count(self) -> int:
		"""Return the number of retained short-term memories."""

		return self.repository.count()

	def _evict_excess(self) -> None:
		for record in self.repository.list()[self.max_items :]:
			self.repository.delete(record.id)
