"""Confidence calculation based on supporting sources and evidence quality."""

from __future__ import annotations

from backend.ai.cognition.schemas import ConfidenceLevel


class ConfidenceEngine:
    """Maps support quality to coarse confidence levels."""

    @staticmethod
    def compute(*, supporting_sources: int, source_quality: float, retrieval_relevance: float, agreement: float, claim_verified: bool, recency: float) -> ConfidenceLevel:
        score = (
            min(supporting_sources, 5) * 0.12
            + source_quality * 0.30
            + retrieval_relevance * 0.25
            + agreement * 0.20
            + (1.0 if claim_verified else 0.0) * 0.10
            + recency * 0.05
        )
        if score >= 0.75 and claim_verified:
            return ConfidenceLevel.HIGH
        if score >= 0.45:
            return ConfidenceLevel.MEDIUM
        if score >= 0.2:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.UNKNOWN
