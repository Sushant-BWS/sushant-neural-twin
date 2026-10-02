"""Builds a final response contract from answer and evidence."""

from __future__ import annotations

from backend.ai.response.schemas import ResponseContract


class ResponseBuilder:
    """Factory for safe response object creation."""

    @staticmethod
    def build(answer: str, confidence: str = "HIGH", reasoning_summary: str = "", evidence: list[dict] | None = None, sources: list[str] | None = None) -> ResponseContract:
        return ResponseContract(
            answer=answer,
            confidence=confidence,
            reasoning_summary=reasoning_summary,
            evidence=evidence or [],
            sources=sources or [],
        )
