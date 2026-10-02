"""Determines intent and retrieval requirements for a user inquiry."""

from __future__ import annotations

from backend.ai.cognition.schemas import QueryPlan, RetrievalMode


class QueryPlanner:
    """Map a user question into concrete retrieval and reasoning decisions."""

    def plan(self, question: str) -> QueryPlan:
        normalized = question.strip().lower()
        intent = "general"
        sources = ["profile", "experience", "projects"]

        if any(token in normalized for token in ["skill", "technical", "stack", "technology"]):
            intent = "skill"
            sources = ["skills", "projects", "experience"]
        elif any(token in normalized for token in ["project", "built", "worked on", "portfolio"]):
            intent = "project"
            sources = ["projects", "experience", "skills"]
        elif any(token in normalized for token in ["study", "education", "degree", "university"]):
            intent = "education"
            sources = ["education", "experience", "profile"]
        elif any(token in normalized for token in ["role", "current job", "career", "position"]):
            intent = "career"
            sources = ["experience", "profile", "projects"]
        elif any(token in normalized for token in ["certif", "azure", "aws", "cloud"]):
            intent = "certification"
            sources = ["certifications", "experience", "projects"]
        elif any(token in normalized for token in ["thought", "learn", "decision", "principle", "preference"]):
            intent = "thought"
            sources = ["thoughts", "projects", "experience"]
        elif any(token in normalized for token in ["who is", "about sushant", "profile"]):
            intent = "profile"
            sources = ["profile", "experience", "education"]

        retrieval_mode = RetrievalMode.HYBRID.value
        if intent in {"profile", "education", "career"}:
            retrieval_mode = RetrievalMode.METADATA.value

        return QueryPlan(
            intent=intent,
            sources=sources,
            retrieval_mode=retrieval_mode,
            memory_required=True,
            reasoning_required=True,
            llm_required=True,
            voice_required=False,
            verification_required=True,
            required_sources=sources,
        )
