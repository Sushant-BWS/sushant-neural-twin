"""Tests for the Phase 7 documented thought engine."""

import unittest

from backend.knowledge import EvidenceType, ThoughtEngine
from backend.knowledge.schemas import Thought


class ThoughtEngineTests(unittest.TestCase):
    """Verify evidence-aware thought storage and retrieval."""

    def setUp(self) -> None:
        self.engine = ThoughtEngine()
        self.engine.add_documented_thought(
            Thought(
                topic="engineering principles",
                statement="Prefer evidence-based design decisions.",
                context="Architecture work",
                evidence=["thoughts/principles.json#0"],
                source="thoughts/principles.json#0",
                confidence=0.9,
            )
        )
        self.engine.add_documented_thought(
            Thought(
                topic="learning",
                statement="Use small experiments to test assumptions.",
                context="Learning workflow",
                evidence=["thoughts/learning.json#0"],
                source="thoughts/learning.json#0",
                confidence=0.8,
            )
        )

    def test_stores_required_traceable_fields(self) -> None:
        thoughts = self.engine.thoughts()

        self.assertEqual(len(thoughts), 2)
        self.assertTrue(thoughts[0].id)
        self.assertTrue(thoughts[0].source)
        self.assertIsNotNone(thoughts[0].created_at)
        self.assertIsNotNone(thoughts[0].updated_at)

    def test_retrieves_relevant_documented_thoughts(self) -> None:
        results = self.engine.search("evidence design")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].thought.topic, "engineering principles")
        self.assertGreater(results[0].score, 0)

    def test_unknown_and_inference_stay_separate(self) -> None:
        unknown = self.engine.assess(EvidenceType.UNKNOWN)
        inference = self.engine.assess(EvidenceType.INFERENCE, ["derived-ref"])
        documented = self.engine.assess(
            EvidenceType.DOCUMENTED_THOUGHT,
            ["thoughts/principles.json#0"],
        )

        self.assertFalse(unknown.supported)
        self.assertEqual(unknown.evidence_type, EvidenceType.UNKNOWN)
        self.assertTrue(inference.supported)
        self.assertEqual(inference.evidence_type, EvidenceType.INFERENCE)
        self.assertTrue(documented.supported)

    def test_fact_and_experience_require_explicit_evidence(self) -> None:
        fact = self.engine.assess(EvidenceType.FACT)
        experience = self.engine.assess(EvidenceType.EXPERIENCE, ["experience.json#0"])

        self.assertFalse(fact.supported)
        self.assertTrue(experience.supported)

    def test_does_not_create_thoughts_from_unmatched_queries(self) -> None:
        before = self.engine.count()

        self.assertEqual(self.engine.search("unrelated unsupported claim"), [])
        self.assertEqual(self.engine.count(), before)

    def test_rejects_incomplete_documented_thoughts(self) -> None:
        with self.assertRaises(ValueError):
            self.engine.add_documented_thought(
                Thought(topic="", statement="statement", source="source")
            )
        with self.assertRaises(ValueError):
            self.engine.add_documented_thought(
                Thought(topic="topic", statement="statement", source="")
            )


if __name__ == "__main__":
    unittest.main()
