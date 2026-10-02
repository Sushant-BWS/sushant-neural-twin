"""Memory management service."""

from __future__ import annotations

from backend.memory.memory_manager import MemoryManager


class MemoryService:
    """Expose working-memory and semantic-memory decisions to API layers."""

    def __init__(self, manager: MemoryManager | None = None) -> None:
        self.manager = manager or MemoryManager()

    def decide(self, intent: str, question: str) -> list[str]:
        return self.manager.decide(intent, question)
