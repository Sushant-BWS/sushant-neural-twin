"""Central selection logic for memory retrieval and persistence."""

from __future__ import annotations

from backend.memory.memory_schemas import MemoryCandidate, WorkingMemory
from backend.memory.working import WorkingMemoryStore


class MemoryManager:
    """Decide which memory systems should be queried for a given task."""

    def __init__(self, working_store: WorkingMemoryStore | None = None) -> None:
        self.working_store = working_store or WorkingMemoryStore()

    def decide(self, intent: str, question: str) -> list[str]:
        systems = ["working_memory", "semantic_memory"]
        lowered = (intent + " " + question).lower()
        if any(token in lowered for token in ["project", "skill", "experience", "career"]):
            systems.append("long_term_memory")
        if any(token in lowered for token in ["learn", "decision", "thought", "principle"]):
            systems.append("thought_memory")
        return systems

    def working_snapshot(self) -> WorkingMemory:
        return self.working_store.snapshot()

    def candidate(self, content: str, memory_type: str, subject: str, **metadata: object) -> MemoryCandidate:
        return MemoryCandidate(
            memory_type=memory_type,
            subject=subject,
            content=content,
            importance=float(metadata.get("importance", 0.0)),
            relevance=float(metadata.get("relevance", 0.0)),
            recency=float(metadata.get("recency", 0.0)),
            confidence=float(metadata.get("confidence", 0.0)),
            source_reliability=float(metadata.get("source_reliability", 0.5)),
            source=str(metadata.get("source", "conversation")),
            metadata=dict(metadata),
        )
