"""Tests for the Phase 4 memory architecture."""

import unittest
from datetime import datetime, timezone

from backend.memory import (
    EpisodicMemory,
    EpisodicMemoryRecord,
    InMemoryMemoryRepository,
    LongTermMemory,
    MemoryRecord,
    ShortTermMemory,
    ThoughtMemory,
    ThoughtMemoryRecord,
)


class MemoryArchitectureTests(unittest.TestCase):
    """Verify traceability and behavior of each memory service."""

    def test_repository_is_traceable_and_ordered(self) -> None:
        repository = InMemoryMemoryRepository()
        first = repository.add(
            MemoryRecord(content="first", source="test", confidence=0.5)
        )
        second = repository.add(
            MemoryRecord(content="second", source="test", confidence=0.6)
        )

        self.assertEqual(repository.count(), 2)
        self.assertEqual(repository.list(), [second, first])
        self.assertIsNotNone(first.created_at.tzinfo)
        self.assertEqual(repository.get(first.id), first)

    def test_short_term_memory_evicts_oldest(self) -> None:
        memory = ShortTermMemory(max_items=2)
        first = memory.add("first", "test", 0.5)
        memory.add("second", "test", 0.6)
        memory.add("third", "test", 0.7)

        self.assertEqual(memory.count(), 2)
        self.assertIsNone(memory.get(first.id))
        self.assertEqual([item.content for item in memory.recent()], ["third", "second"])

    def test_long_term_memory_preserves_source_and_confidence(self) -> None:
        memory = LongTermMemory()

        record = memory.remember("durable fact", "profile.json", 0.9)

        self.assertEqual(record.source, "profile.json")
        self.assertEqual(record.confidence, 0.9)
        self.assertEqual(memory.count(), 1)

    def test_episodic_memory_preserves_occurrence_time(self) -> None:
        occurred_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        memory = EpisodicMemory()

        event = memory.record_event("event", "conversation.json", 0.8, occurred_at)

        self.assertIsInstance(event, EpisodicMemoryRecord)
        self.assertEqual(event.occurred_at, occurred_at)

    def test_thought_memory_requires_topic_and_keeps_evidence(self) -> None:
        memory = ThoughtMemory()

        thought = memory.remember(
            "engineering",
            "documented statement",
            "thoughts.json",
            0.85,
            evidence=["thoughts.json#0"],
        )

        self.assertIsInstance(thought, ThoughtMemoryRecord)
        self.assertEqual(thought.evidence, ["thoughts.json#0"])
        with self.assertRaises(ValueError):
            memory.remember("", "statement", "thoughts.json", 0.5)

    def test_memory_confidence_must_be_between_zero_and_one(self) -> None:
        with self.assertRaises(ValueError):
            ShortTermMemory().add("invalid", "test", 1.1)


if __name__ == "__main__":
    unittest.main()
