"""Formats evidence into a minimal, user-safe payload."""

from __future__ import annotations


class EvidenceFormatter:
    """Render evidence items without leaking internal chain-of-thought."""

    @staticmethod
    def format(evidence: list[dict] | None) -> list[dict]:
        return [
            {
                "source": item.get("source", "unknown"),
                "summary": item.get("summary", "Documented evidence"),
            }
            for item in (evidence or [])
        ]
