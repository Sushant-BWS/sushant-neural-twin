"""Relevance scoring that balances recency, frequency, and importance."""

from __future__ import annotations


class MemoryRelevance:
    """Compute a weighted relevance score for memory candidates."""

    @staticmethod
    def score(
        recency: float,
        frequency: float = 0.0,
        importance: float = 0.0,
        relevance: float = 0.0,
        confidence: float = 0.0,
    ) -> float:
        weighted = (
            0.30 * recency
            + 0.20 * frequency
            + 0.25 * importance
            + 0.15 * relevance
            + 0.10 * confidence
        )
        return max(0.0, min(1.0, weighted))
