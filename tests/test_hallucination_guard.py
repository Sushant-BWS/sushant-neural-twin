"""Tests for the Phase 10 hallucination guard."""

import unittest

from backend.ai import ClaimStatus, HallucinationGuard, SearchResult
from backend.knowledge.store import KnowledgeDocument


class HallucinationGuardTests(unittest.TestCase):
    """Verify claim statuses and guarded answer behavior."""

    def setUp(self) -> None:
        self.guard = HallucinationGuard()
        self.evidence = [
            SearchResult(
                document=KnowledgeDocument(
                    id="project-1",
                    content="Sushant uses Python for backend engineering.",
                    metadata={"source": "projects/projects.json#0"},
                ),
                score=0.95,
            )
        ]

    def test_classifies_verified_claim(self) -> None:
        verification = self.guard.verify_claim(
            "Sushant uses Python for backend engineering.",
            self.evidence,
        )

        self.assertEqual(verification.status, ClaimStatus.VERIFIED)
        self.assertEqual(verification.evidence[0].source, "projects/projects.json#0")

    def test_classifies_supported_claim(self) -> None:
        verification = self.guard.verify_claim(
            "Sushant uses Python backend engineering.",
            self.evidence,
        )

        self.assertEqual(verification.status, ClaimStatus.SUPPORTED)
        self.assertGreaterEqual(verification.overlap, 0.6)

    def test_classifies_uncertain_and_unknown_claims(self) -> None:
        uncertain = self.guard.verify_claim("Sushant is an astronaut.", self.evidence)
        unknown = self.guard.verify_claim("Quantum astronomy is documented.", self.evidence)

        self.assertEqual(uncertain.status, ClaimStatus.UNCERTAIN)
        self.assertEqual(unknown.status, ClaimStatus.UNKNOWN)

    def test_rejects_mixed_answer_with_unsupported_claim(self) -> None:
        guarded = self.guard.guard_answer(
            "Sushant uses Python for backend engineering. Quantum astronomy is documented.",
            self.evidence,
        )

        self.assertFalse(guarded.safe)
        self.assertEqual(guarded.answer, self.guard.insufficient_message)
        self.assertEqual(len(guarded.verifications), 2)

    def test_accepts_answer_when_all_claims_are_supported(self) -> None:
        answer = "Sushant uses Python for backend engineering."

        guarded = self.guard.guard_answer(answer, self.evidence)

        self.assertTrue(guarded.safe)
        self.assertEqual(guarded.answer, answer)
        self.assertEqual(guarded.verifications[0].status, ClaimStatus.VERIFIED)

    def test_empty_claim_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.guard.verify_claim("   ", self.evidence)


if __name__ == "__main__":
    unittest.main()
