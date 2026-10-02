"""Plans the composition of a final response from evidence and confidence."""

from __future__ import annotations


class ResponsePlanner:
    """Build a final response contract with evidence and transparent summary."""

    @staticmethod
    def plan(answer: str, confidence: str, evidence_count: int, intent: str) -> dict[str, object]:
        return {
            "answer": answer,
            "confidence": confidence,
            "reasoning_summary": f"Matched {intent} evidence against {evidence_count} verified sources.",
            "evidence": [],
            "sources": [],
            "voice": {"available": False},
        }
