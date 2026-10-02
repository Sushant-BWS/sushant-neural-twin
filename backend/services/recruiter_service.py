"""Recruiter-facing model helper service."""

from __future__ import annotations


class RecruiterService:
    def summarize(self, content: str) -> str:
        return f"Recruiter summary: {content[:120]}"
