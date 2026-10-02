"""High-level decision engine for choosing the best supported answer."""

from __future__ import annotations


class DecisionEngine:
    """Pick the most defensible answer when evidence is mixed or incomplete."""

    @staticmethod
    def choose(best_answer: str, alternatives: list[str] | None = None) -> str:
        if not best_answer:
            return alternatives[0] if alternatives else "I do not have enough verified information to answer confidently."
        return best_answer
