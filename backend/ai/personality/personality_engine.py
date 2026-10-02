"""Classifies output type to keep inferences distinguishable from facts."""

from __future__ import annotations

from enum import Enum


class FactType(str, Enum):
    FACT = "fact"
    PERSONAL_PREFERENCE = "personal_preference"
    DOCUMENTED_THOUGHT = "documented_thought"
    INFERENCE = "inference"
    UNKNOWN = "unknown"


class PersonalityEngine:
    """Assign trust labels to user-facing statements."""

    @staticmethod
    def classify(statement: str) -> FactType:
        lowered = statement.lower()
        if any(token in lowered for token in ["i prefer", "i like", "i enjoy"]):
            return FactType.PERSONAL_PREFERENCE
        if any(token in lowered for token in ["principle", "learning", "decision", "belief"]):
            return FactType.DOCUMENTED_THOUGHT
        if any(token in lowered for token in ["likely", "probably", "suggests", "seems"]):
            return FactType.INFERENCE
        return FactType.FACT
