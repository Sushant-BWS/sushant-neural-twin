"""Response style policy."""

from __future__ import annotations


class ResponseStyle:
    """Recommendation for final answer wording."""

    @staticmethod
    def style() -> str:
        return "Short, grounded, and actionable"
