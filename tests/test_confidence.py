"""Tests for the Phase 12 confidence and evaluation engine."""

import unittest

from backend.ai import ClaimStatus, ClaimVerification
from backend.ml import (
    ConfidenceEngine,
    ConfidenceFactors,
    ConfidenceLevel,
    EvaluationExample,
)


class ConfidenceEngineTests(unittest.TestCase):
    """Verify transparent confidence estimates and evaluation metrics."""

    def setUp(self) -> None:
        self.engine = ConfidenceEngine()

    def test_high_and_low_estimates_are_bounded(self) -> None:
        high = self.engine.estimate(
            ConfidenceFactors(
                source_quality=1,
                supporting_sources=3,
                retrieval_relevance=1,
                data_freshness=1,
                evidence_completeness=1,
            )
        )
        low = self.engine.estimate(
            ConfidenceFactors(
                source_quality=0.2,
                supporting_sources=0,
                retrieval_relevance=0.1,
                data_freshness=0.1,
                contradictions=2,
                evidence_completeness=0.1,
            )
        )

        self.assertEqual(high.confidence_level, ConfidenceLevel.HIGH)
        self.assertEqual(low.confidence_level, ConfidenceLevel.LOW)
        self.assertGreaterEqual(high.confidence, 0)
        self.assertLessEqual(high.confidence, 1)
        self.assertLess(low.confidence, high.confidence)

    def test_factors_change_the_estimate(self) -> None:
        base = self.engine.estimate(ConfidenceFactors())
        stronger = self.engine.estimate(
            ConfidenceFactors(
                source_quality=0.9,
                supporting_sources=2,
                retrieval_relevance=0.8,
                data_freshness=0.9,
                evidence_completeness=0.8,
            )
        )

        self.assertGreater(stronger.confidence, base.confidence)
        self.assertIn("source quality", stronger.rationale)

    def test_verification_integration_penalizes_unsupported_claims(self) -> None:
        supported = ClaimVerification(
            claim="documented claim",
            status=ClaimStatus.SUPPORTED,
            overlap=0.8,
            evidence=[],
            rationale="supported",
        )
        unknown = ClaimVerification(
            claim="unknown claim",
            status=ClaimStatus.UNKNOWN,
            overlap=0.0,
            evidence=[],
            rationale="unknown",
        )

        supported_estimate = self.engine.from_verification(supported)
        unknown_estimate = self.engine.from_verification(unknown)

        self.assertGreater(supported_estimate.confidence, unknown_estimate.confidence)
        self.assertEqual(unknown_estimate.factors.contradictions, 1)

    def test_evaluates_directional_accuracy(self) -> None:
        high = self.engine.estimate(
            ConfidenceFactors(
                source_quality=1,
                supporting_sources=3,
                retrieval_relevance=1,
                data_freshness=1,
                evidence_completeness=1,
            )
        )
        low = self.engine.estimate(ConfidenceFactors())

        report = self.engine.evaluate(
            [
                EvaluationExample(estimate=high, supported=True),
                EvaluationExample(estimate=low, supported=False),
            ]
        )

        self.assertEqual(report.total, 2)
        self.assertEqual(report.correct_direction, 2)
        self.assertEqual(report.directional_accuracy, 1.0)

    def test_empty_evaluation_is_defined(self) -> None:
        report = self.engine.evaluate([])

        self.assertEqual(report.total, 0)
        self.assertEqual(report.directional_accuracy, 0.0)
        self.assertEqual(report.mean_confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
