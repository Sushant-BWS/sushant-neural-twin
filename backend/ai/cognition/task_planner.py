"""Determines the work units required to answer a query."""

from __future__ import annotations


class TaskPlanner:
    """Convert a query into a short list of execution tasks."""

    def plan(self, question: str, intent: str) -> list[str]:
        tasks = ["retrieve_context", "evaluate_evidence", "compose_answer"]
        lowered = question.lower()
        if any(token in lowered for token in ["who", "what", "profile", "role"]):
            tasks.insert(1, "extract_entities")
        if any(token in lowered for token in ["learn", "preference", "principle", "decision"]):
            tasks.append("check_memory")
        return tasks
