"""Conversation summarization helper."""

from __future__ import annotations


class ConversationSummarizer:
    @staticmethod
    def summarize(history: list[str]) -> str:
        return " | ".join(history[-4:]) if history else "No conversation yet."
