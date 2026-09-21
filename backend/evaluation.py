"""Evaluation metrics for the personal AI system's measurable behaviors."""

from collections.abc import Iterable, Sequence
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.ai.hallucination_guard import ClaimStatus, GuardedAnswer
from backend.ml.confidence import ConfidenceEngine, EvaluationExample, EvaluationReport
from backend.ml.intent_classifier import (
    Intent,
    IntentEvaluation,
    IntentExample,
    RuleBasedIntentClassifier,
)


class EvaluationCategory(StrEnum):
    """Evaluation dimensions tracked by Phase 16."""

    FACTUAL_ACCURACY = "factual_accuracy"
    RETRIEVAL_ACCURACY = "retrieval_accuracy"
    HALLUCINATION = "hallucination"
    INTENT_CLASSIFICATION = "intent_classification"
    CONFIDENCE_CALIBRATION = "confidence_calibration"
    CONSISTENCY = "consistency"


class MetricResult(BaseModel):
    """One bounded evaluation metric."""

    model_config = ConfigDict(frozen=True)

    category: EvaluationCategory
    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    score: float = Field(ge=0, le=1)
    details: str


class EvaluationReport(BaseModel):
    """Collection of measured metrics for one evaluation run."""

    model_config = ConfigDict(frozen=True)

    metrics: list[MetricResult] = Field(default_factory=list)

    @property
    def overall_score(self) -> float:
        """Return the unweighted mean of available metric scores."""

        if not self.metrics:
            return 0.0
        return sum(metric.score for metric in self.metrics) / len(self.metrics)


class EvaluationSuite:
    """Run deterministic evaluations over supplied expected and actual values."""

    def factual_accuracy(
        self,
        expected: Sequence[str],
        actual: Sequence[str],
    ) -> MetricResult:
        """Measure normalized exact-match factual answers."""

        pairs = list(zip(expected, actual, strict=False))
        passed = sum(self._normalize(left) == self._normalize(right) for left, right in pairs)
        return self._metric(
            EvaluationCategory.FACTUAL_ACCURACY,
            len(expected),
            passed,
            "Normalized exact-match factual answer accuracy.",
        )

    def retrieval_accuracy(
        self,
        expected_ids: Sequence[set[str]],
        actual_ids: Sequence[Sequence[str]],
    ) -> MetricResult:
        """Measure whether expected document IDs were retrieved."""

        pairs = list(zip(expected_ids, actual_ids, strict=False))
        passed = sum(bool(expected & set(actual)) for expected, actual in pairs)
        return self._metric(
            EvaluationCategory.RETRIEVAL_ACCURACY,
            len(expected_ids),
            passed,
            "Case passes when at least one expected document is retrieved.",
        )

    def hallucination_safety(
        self,
        answers: Iterable[GuardedAnswer],
        expected_safe: Sequence[bool],
    ) -> MetricResult:
        """Measure agreement between guard safety and expected safety labels."""

        answer_list = list(answers)
        pairs = list(zip(answer_list, expected_safe, strict=False))
        passed = sum(answer.safe is expected for answer, expected in pairs)
        return self._metric(
            EvaluationCategory.HALLUCINATION,
            len(expected_safe),
            passed,
            "Agreement between hallucination guard output and safety labels.",
        )

    def intent_accuracy(
        self,
        examples: Iterable[IntentExample],
        classifier: RuleBasedIntentClassifier | None = None,
    ) -> MetricResult:
        """Measure exact intent-label accuracy."""

        evaluation: IntentEvaluation = (classifier or RuleBasedIntentClassifier()).evaluate(examples)
        return self._metric(
            EvaluationCategory.INTENT_CLASSIFICATION,
            evaluation.total,
            evaluation.correct,
            "Exact-label accuracy from the interpretable intent baseline.",
        )

    def confidence_calibration(
        self,
        examples: Iterable[EvaluationExample],
        engine: ConfidenceEngine | None = None,
    ) -> MetricResult:
        """Measure directional confidence accuracy against support labels."""

        evaluation: EvaluationReport = (engine or ConfidenceEngine()).evaluate(examples)
        return self._metric(
            EvaluationCategory.CONFIDENCE_CALIBRATION,
            evaluation.total,
            evaluation.correct_direction,
            "Directional accuracy at the 0.5 confidence threshold.",
        )

    def consistency(self, outputs: Sequence[str]) -> MetricResult:
        """Measure exact repeat consistency for identical evaluation inputs."""

        total = max(0, len(outputs) - 1)
        if not outputs:
            return self._metric(
                EvaluationCategory.CONSISTENCY,
                0,
                0,
                "No repeated outputs supplied.",
            )
        expected = self._normalize(outputs[0])
        passed = sum(self._normalize(output) == expected for output in outputs[1:])
        return self._metric(
            EvaluationCategory.CONSISTENCY,
            total,
            passed,
            "Exact normalized agreement with the first repeated output.",
        )

    def run(self, metrics: Iterable[MetricResult]) -> EvaluationReport:
        """Assemble previously measured metrics into one report."""

        return EvaluationReport(metrics=list(metrics))

    @staticmethod
    def _normalize(value: Any) -> str:
        return " ".join(str(value).strip().lower().split())

    @staticmethod
    def _metric(
        category: EvaluationCategory,
        total: int,
        passed: int,
        details: str,
    ) -> MetricResult:
        score = passed / total if total else 0.0
        return MetricResult(
            category=category,
            total=total,
            passed=passed,
            score=score,
            details=details,
        )
