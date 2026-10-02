"""Defines communication style helpers."""

from __future__ import annotations


class CommunicationStyle:
    """Keep the assistant readable and grounded."""

    @staticmethod
    def concise() -> str:
        return "brief and evidence-based"

    @staticmethod
    def balanced() -> str:
        return "clear, friendly, and grounded"
