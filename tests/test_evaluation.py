"""Tests for the Phase 16 evaluation suite and synthetic dataset."""

import unittest

from backend.ai import ClaimEvidence, GuardedAnswer
from backend.evaluation import EvaluationCategory, EvaluationSuite
from backend.ml import ConfidenceEngine, ConfidenceFactors, EvaluationExample
from tests.evaluation_dataset import (
    CONSISTENT_OUTPUTS,
    FACTUAL_CASES,
    INTENT_CASES,
    RETRIEVAL_CASES,
)


class EvaluationSuiteTests(unittest.TestCase):
    """Verify measurable evaluation categories and bounded metrics."""

    def setUp(self) -> None:
        self.suite = EvaluationSuite()

    def test_factual_accuracy_is_measured(self) -> None:
        result = self.suite.factual_accuracy(
            [expected for expected, _ in FACTUAL_CASES],
            [actual for _, actual in FACTUAL_CASES],
        )

        self.assertEqual(result.category, EvaluationCategory.FACTUAL_ACCURACY)
        self.assertEqual(result.total, 3)
        self.assertEqual(result.passed, 2)
        self.assertAlmostEqual(result.score, 2 / 3)

    def test_retrieval_accuracy_is_measured(self) -> None:
        expected = [case[0] for case in RETRIEVAL_CASES]
        actual = [case[1] for case in RETRIEVAL_CASES]

        result = self.suite.retrieval_accuracy(expected, actual)

        self.assertEqual(result.total, 3)
        self.assertEqual(result.passed, 2)

    def test_hallucination_safety_is_measured(self) -> None:
        answers = [
            GuardedAnswer(answer="supported", safe=True),
            GuardedAnswer(answer="fallback", safe=False),
            GuardedAnswer(answer="wrongly accepted", safe=True),
        ]

        result = self.suite.hallucination_safety(answers, [True, False, False])

        self.assertEqual(result.category, EvaluationCategory.HALLUCINATION)
        self.assertEqual(result.passed, 2)

    def test_intent_and_confidence_metrics_are_measured(self) -> None:
        intent_result = self.suite.intent_accuracy(INTENT_CASES)
        confidence_engine = ConfidenceEngine()
        supported = confidence_engine.estimate(
            ConfidenceFactors(
                source_quality=1,
                supporting_sources=3,
                retrieval_relevance=1,
                data_freshness=1,
                evidence_completeness=1,
            )
        )
        unsupported = confidence_engine.estimate(ConfidenceFactors())
        confidence_result = self.suite.confidence_calibration(
            [
                EvaluationExample(estimate=supported, supported=True),
                EvaluationExample(estimate=unsupported, supported=False),
            ]
        )

        self.assertEqual(intent_result.score, 1.0)
        self.assertEqual(confidence_result.score, 1.0)

    def test_consistency_normalizes_whitespace(self) -> None:
        result = self.suite.consistency(CONSISTENT_OUTPUTS)

        self.assertEqual(result.category, EvaluationCategory.CONSISTENCY)
        self.assertEqual(result.total, 2)
        self.assertEqual(result.passed, 2)
        self.assertEqual(result.score, 1.0)

    def test_report_aggregates_measured_metrics(self) -> None:
        factual = self.suite.factual_accuracy(["a"], ["a"])
        consistency = self.suite.consistency(["same", "same"])
        report = self.suite.run([factual, consistency])

        self.assertEqual(len(report.metrics), 2)
        self.assertEqual(report.overall_score, 1.0)

    def test_metrics_are_bounded_and_empty_inputs_are_defined(self) -> None:
        result = self.suite.consistency([])
        report = self.suite.run([result])

        self.assertEqual(result.score, 0.0)
        self.assertGreaterEqual(report.overall_score, 0)
        self.assertLessEqual(report.overall_score, 1)


if __name__ == "__main__":
    unittest.main()
