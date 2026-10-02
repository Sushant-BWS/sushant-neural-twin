"""Working memory for the active conversation and task context."""

from __future__ import annotations

from backend.memory.memory_schemas import WorkingMemory


class WorkingMemoryStore:
    """Manage the current conversation state without persisting everything."""

    def __init__(self) -> None:
        self._memory = WorkingMemory()

    def update(self, **kwargs: object) -> WorkingMemory:
        for key, value in kwargs.items():
            if hasattr(self._memory, key):
                setattr(self._memory, key, value)
        self._memory.updated_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        return self._memory

    def snapshot(self) -> WorkingMemory:
        return self._memory

    def reset(self) -> None:
        self._memory = WorkingMemory()
