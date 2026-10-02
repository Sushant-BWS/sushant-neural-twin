"""Formats a final answer for the user while hiding hidden reasoning details."""

from __future__ import annotations


class ResponseFormatter:
    """Renders the final answer and metadata for API output."""

    @staticmethod
    def format(answer: str, confidence: str, reasoning_summary: str, evidence_count: int = 0) -> dict[str, object]:
        return {
            "answer": answer,
            "confidence": confidence,
            "reasoning_summary": reasoning_summary,
            "evidence_count": evidence_count,
            "intent": "detected",
            "voice": {"available": True},
        }
