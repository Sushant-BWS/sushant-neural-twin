"""Documented thought memory service."""

from datetime import datetime
from typing import Any

from pydantic import Field

from backend.memory.base import (
	InMemoryMemoryRepository,
	MemoryRecord,
	MemoryRepository,
)


class ThoughtMemoryRecord(MemoryRecord):
	"""A traceable thought with topic and supporting evidence references."""

	topic: str = Field(min_length=1)
	evidence: list[str] = Field(default_factory=list)


class ThoughtMemory:
	"""Manage documented thoughts without inferring new personal attributes."""

	def __init__(self, repository: MemoryRepository | None = None) -> None:
		self.repository = repository or InMemoryMemoryRepository()

	def remember(
		self,
		topic: str,
		statement: str,
		source: str,
		confidence: float,
		evidence: list[str] | None = None,
		metadata: dict[str, Any] | None = None,
		created_at: datetime | None = None,
	) -> ThoughtMemoryRecord:
		"""Store a documented thought and its evidence references."""

		record = ThoughtMemoryRecord(
			topic=topic,
			content=statement,
			source=source,
			confidence=confidence,
			evidence=list(evidence or []),
			metadata=dict(metadata or {}),
			**({"created_at": created_at} if created_at else {}),
		)
		stored = self.repository.add(record)
		return ThoughtMemoryRecord.model_validate(stored.model_dump())

	def get(self, record_id: str) -> ThoughtMemoryRecord | None:
		"""Return a thought memory by identifier."""

		record = self.repository.get(record_id)
		return ThoughtMemoryRecord.model_validate(record.model_dump()) if record else None

	def thoughts(self, limit: int | None = None) -> list[ThoughtMemoryRecord]:
		"""Return documented thoughts from newest to oldest."""

		return [
			ThoughtMemoryRecord.model_validate(record.model_dump())
			for record in self.repository.list(limit)
		]

	def clear(self) -> None:
		"""Clear all thought memories."""

		self.repository.clear()

	def count(self) -> int:
		"""Return the number of thought memories."""

		return self.repository.count()
