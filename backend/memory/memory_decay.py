"""Soft-decay logic for memory relevance over time."""

from __future__ import annotations

from datetime import datetime, timezone


class MemoryDecay:
    """Calculates a soft-decay score without deleting important memories."""

    @staticmethod
    def score(age_days: float, half_life_days: float = 30.0) -> float:
        if age_days < 0:
            return 1.0
        if half_life_days <= 0:
            return 1.0
        decay = 0.5 ** (age_days / half_life_days)
        return max(0.0, min(1.0, decay))

    @staticmethod
    def from_timestamp(timestamp: datetime | None, now: datetime | None = None) -> float:
        now = now or datetime.now(timezone.utc)
        if timestamp is None:
            return 1.0
        delta = max((now - timestamp).total_seconds() / 86400.0, 0.0)
        return MemoryDecay.score(delta)
