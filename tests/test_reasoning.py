"""Tests for the Phase 9 evidence-based reasoning engine."""

import unittest

from backend.ai import (
    ReasoningEngine,
    ReasoningIntent,
    ReasoningRequest,
    SearchResult,
)
from backend.knowledge.schemas import Thought
from backend.knowledge.store import KnowledgeDocument
from backend.knowledge.thought_engine import ThoughtEngine


class ReasoningEngineTests(unittest.TestCase):
    """Verify concise evidence synthesis without private reasoning traces."""

    def setUp(self) -> None:
        self.engine = ReasoningEngine()

    @staticmethod
    def search_result(
        document_id: str,
        content: str,
        source: str,
        score: float,
    ) -> SearchResult:
        return SearchResult(
            document=KnowledgeDocument(
                id=document_id,
                content=content,
                metadata={"source": source},
            ),
            score=score,
        )

    def test_returns_insufficient_evidence_without_sources(self) -> None:
        response = self.engine.reason(
            ReasoningRequest(question="What is documented?", intent=ReasoningIntent.PROFILE)
        )

        self.assertFalse(response.sufficient_evidence)
        self.assertEqual(response.evidence_count, 0)
        self.assertIn("don't have enough verified", response.answer)
        self.assertEqual(response.evidence, [])

    def test_synthesizes_facts_and_experiences_with_references(self) -> None:
        fact = self.search_result("fact-1", "A documented skill.", "facts.json#0", 0.95)
        experience = self.search_result(
            "experience-1",
            "A documented project experience.",
            "experience.json#0",
            0.88,
        )

        response = self.engine.reason(
            ReasoningRequest(question="What is relevant?", intent=ReasoningIntent.EXPERIENCE),
            facts=[fact],
            experiences=[experience],
        )

        self.assertTrue(response.sufficient_evidence)
        self.assertEqual(response.evidence_count, 2)
        self.assertEqual(
            [reference.source for reference in response.evidence],
            ["facts.json#0", "experience.json#0"],
        )
        self.assertIn("2 documented sources", response.reasoning_summary)
        self.assertIn("A documented skill.", response.answer)

    def test_integrates_documented_thoughts(self) -> None:
        thought_engine = ThoughtEngine()
        thought_engine.add_documented_thought(
            Thought(
                topic="engineering",
                statement="Prefer evidence-based decisions.",
                source="thoughts/principles.json#0",
                confidence=0.9,
                evidence=["thoughts/principles.json#0"],
            )
        )
        thought = thought_engine.search("evidence decisions")[0]

        response = self.engine.reason(
            ReasoningRequest(question="What principle is documented?", intent=ReasoningIntent.THOUGHT),
            thoughts=[thought],
        )

        self.assertEqual(response.evidence[0].evidence_type, "DOCUMENTED_THOUGHT")
        self.assertIn("Prefer evidence-based decisions.", response.answer)

    def test_ignores_evidence_without_source_reference(self) -> None:
        result = self.search_result("untraceable", "Unsupported content.", "", 0.9)

        response = self.engine.reason(
            ReasoningRequest(question="What is known?"),
            facts=[result],
        )

        self.assertFalse(response.sufficient_evidence)
        self.assertEqual(response.evidence_count, 0)

    def test_response_has_summary_not_chain_of_thought(self) -> None:
        response = self.engine.reason(
            ReasoningRequest(question="What is known?"),
        )

        self.assertTrue(hasattr(response, "reasoning_summary"))
        self.assertFalse(hasattr(response, "chain_of_thought"))
        self.assertFalse(hasattr(response, "internal_reasoning"))


if __name__ == "__main__":
    unittest.main()
