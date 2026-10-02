"""Central orchestration for the Cognitive Personal AI system."""

from __future__ import annotations

from backend.ai.cognition.confidence_engine import ConfidenceEngine
from backend.ai.cognition.context_builder import ContextBuilder
from backend.ai.cognition.planner import QueryPlanner
from backend.ai.cognition.reasoning_summary import ReasoningSummaryBuilder
from backend.ai.cognition.schemas import ConfidenceLevel


class CognitiveEngine:
    """Coordinate question understanding, planning, retrieval, reasoning, and response assembly."""

    def __init__(self) -> None:
        self.planner = QueryPlanner()
        self.context_builder = ContextBuilder()
        self.confidence_engine = ConfidenceEngine()

    def process(self, question: str, evidence: list | None = None, history: list[str] | None = None) -> dict[str, object]:
        plan = self.planner.plan(question)
        context = self.context_builder.build(question, plan.intent, evidence=evidence, history=history)
        confidence = self.confidence_engine.compute(
            supporting_sources=max(1, len(evidence) if evidence else 1),
            source_quality=0.75,
            retrieval_relevance=0.8,
            agreement=0.8,
            claim_verified=bool(evidence),
            recency=0.7,
        )
        reasoning = ReasoningSummaryBuilder.build(
            plan.intent,
            len(evidence or []),
            confidence.value,
            question,
        )
        answer = f"I can help with that {plan.intent} request. {reasoning}"
        return {
            "plan": plan.to_dict(),
            "context": context,
            "confidence": confidence,
            "reasoning_summary": reasoning,
            "answer": answer,
            "summary": reasoning,
        }
