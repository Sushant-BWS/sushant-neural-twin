"""Transparent confidence estimation for evidence-backed responses."""

from collections.abc import Iterable
from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from backend.ai.hallucination_guard import ClaimStatus, ClaimVerification


class ConfidenceLevel(StrEnum):
	"""Human-readable confidence bands for an estimated score."""

	HIGH = "HIGH"
	MEDIUM = "MEDIUM"
	LOW = "LOW"


class ConfidenceFactors(BaseModel):
	"""Inputs contributing to an estimated confidence score."""

	source_quality: float = Field(default=0.5, ge=0, le=1)
	supporting_sources: int = Field(default=0, ge=0)
	retrieval_relevance: float = Field(default=0, ge=0, le=1)
	data_freshness: float = Field(default=0.5, ge=0, le=1)
	contradictions: int = Field(default=0, ge=0)
	evidence_completeness: float = Field(default=0, ge=0, le=1)


class ConfidenceEstimate(BaseModel):
	"""An estimated confidence result with auditable factors."""

	model_config = ConfigDict(frozen=True)

	confidence: float = Field(ge=0, le=1)
	confidence_level: ConfidenceLevel
	factors: ConfidenceFactors
	rationale: str


class EvaluationExample(BaseModel):
	"""A labeled confidence example for calibration diagnostics."""

	estimate: ConfidenceEstimate
	supported: bool


class EvaluationReport(BaseModel):
	"""Simple evaluation metrics for confidence estimates."""

	total: int = Field(ge=0)
	correct_direction: int = Field(ge=0)
	directional_accuracy: float = Field(ge=0, le=1)
	mean_confidence: float = Field(ge=0, le=1)


class ConfidenceEngine:
	"""Estimate confidence from evidence quality without claiming certainty."""

	def estimate(self, factors: ConfidenceFactors) -> ConfidenceEstimate:
		"""Calculate a bounded weighted confidence estimate."""

		source_support = min(1.0, factors.supporting_sources / 3)
		contradiction_penalty = min(0.5, factors.contradictions * 0.15)
		score = (
			factors.source_quality * 0.2
			+ source_support * 0.2
			+ factors.retrieval_relevance * 0.2
			+ factors.data_freshness * 0.15
			+ factors.evidence_completeness * 0.25
			- contradiction_penalty
		)
		confidence = max(0.0, min(1.0, score))
		level = self._level(confidence)
		return ConfidenceEstimate(
			confidence=confidence,
			confidence_level=level,
			factors=factors,
			rationale=self._rationale(level, factors.contradictions),
		)

	def from_verification(
		self,
		verification: ClaimVerification,
		source_quality: float = 0.8,
		data_freshness: float = 0.5,
	) -> ConfidenceEstimate:
		"""Estimate confidence directly from a hallucination-guard result."""

		supported = verification.status in {ClaimStatus.VERIFIED, ClaimStatus.SUPPORTED}
		factors = ConfidenceFactors(
			source_quality=source_quality,
			supporting_sources=len(verification.evidence),
			retrieval_relevance=verification.overlap,
			data_freshness=data_freshness,
			contradictions=0 if supported else 1,
			evidence_completeness=verification.overlap,
		)
		return self.estimate(factors)

	def evaluate(self, examples: Iterable[EvaluationExample]) -> EvaluationReport:
		"""Report directional accuracy and mean estimated confidence."""

		items = list(examples)
		correct = sum(
			(example.estimate.confidence >= 0.5) is example.supported
			for example in items
		)
		total = len(items)
		mean = sum(example.estimate.confidence for example in items) / total if total else 0.0
		return EvaluationReport(
			total=total,
			correct_direction=correct,
			directional_accuracy=correct / total if total else 0.0,
			mean_confidence=mean,
		)

	@staticmethod
	def _level(confidence: float) -> ConfidenceLevel:
		if confidence >= 0.75:
			return ConfidenceLevel.HIGH
		if confidence >= 0.45:
			return ConfidenceLevel.MEDIUM
		return ConfidenceLevel.LOW

	@staticmethod
	def _rationale(level: ConfidenceLevel, contradictions: int) -> str:
		if contradictions:
			return f"{level.value.title()} estimate reduced because contradictory evidence was recorded."
		return f"{level.value.title()} estimate based on source quality, relevance, freshness, and evidence completeness."
