"""Build safe reasoning summaries that do not expose chain-of-thought."""

from __future__ import annotations


class ReasoningSummaryBuilder:
    """Create a human-readable summary without revealing hidden reasoning steps."""

    @staticmethod
    def build(intent: str, evidence_count: int, confidence: str, question: str) -> str:
        target = intent or "general"
        normalized = confidence.upper() if confidence else "UNKNOWN"
        return (
            f"Matched the requested {target} information against documented sources. "
            f"Verified {evidence_count} evidence items and assessed confidence as {normalized}."
        )
