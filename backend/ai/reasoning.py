"""Evidence-based reasoning orchestration without private chain-of-thought."""

from collections.abc import Iterable
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from backend.ai.retrieval import SearchResult
from backend.knowledge.thought_engine import ThoughtSearchResult


class ReasoningIntent(StrEnum):
	"""High-level question categories accepted by the reasoning engine."""

	GENERAL = "GENERAL"
	PROFILE = "PROFILE"
	EXPERIENCE = "EXPERIENCE"
	PROJECT = "PROJECT"
	SKILL = "SKILL"
	THOUGHT = "THOUGHT"
	CAREER = "CAREER"


class ReasoningRequest(BaseModel):
	"""A question and explicit intent for evidence synthesis."""

	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

	question: str = Field(min_length=1)
	intent: ReasoningIntent = ReasoningIntent.GENERAL


class EvidenceReference(BaseModel):
	"""A concise reference to retrieved evidence."""

	source: str = Field(min_length=1)
	evidence_type: str = Field(min_length=1)
	document_id: str = Field(min_length=1)
	score: float | None = Field(default=None, ge=-1, le=1)


class ReasoningResponse(BaseModel):
	"""Evidence-backed answer without private reasoning traces."""

	model_config = ConfigDict(frozen=True)

	answer: str
	reasoning_summary: str
	evidence: list[EvidenceReference] = Field(default_factory=list)
	evidence_count: int = Field(ge=0)
	sufficient_evidence: bool


class ReasoningEngine:
	"""Synthesize concise responses from caller-supplied evidence only."""

	def reason(
		self,
		request: ReasoningRequest,
		facts: Iterable[SearchResult] = (),
		experiences: Iterable[SearchResult] = (),
		thoughts: Iterable[ThoughtSearchResult] = (),
	) -> ReasoningResponse:
		"""Create an answer and evidence summary from explicit retrieved items."""

		references: list[EvidenceReference] = []
		excerpts: list[str] = []
		self._collect_search_results(facts, "FACT", references, excerpts)
		self._collect_search_results(experiences, "EXPERIENCE", references, excerpts)
		self._collect_thoughts(thoughts, references, excerpts)

		if not references:
			return ReasoningResponse(
				answer="I don't have enough verified information to answer that.",
				reasoning_summary="No retrieved evidence was provided.",
				evidence_count=0,
				sufficient_evidence=False,
			)

		evidence_count = len(references)
		summary = self._summary(request.intent, evidence_count)
		answer = " ".join(excerpts)
		return ReasoningResponse(
			answer=answer,
			reasoning_summary=summary,
			evidence=references,
			evidence_count=evidence_count,
			sufficient_evidence=True,
		)

	@staticmethod
	def _collect_search_results(
		results: Iterable[SearchResult],
		evidence_type: str,
		references: list[EvidenceReference],
		excerpts: list[str],
	) -> None:
		for result in results:
			source = str(result.document.metadata.get("source", "")).strip()
			if not source:
				continue
			references.append(
				EvidenceReference(
					source=source,
					evidence_type=evidence_type,
					document_id=result.document.id,
					score=result.score,
				)
			)
			excerpts.append(result.document.content)

	@staticmethod
	def _collect_thoughts(
		results: Iterable[ThoughtSearchResult],
		references: list[EvidenceReference],
		excerpts: list[str],
	) -> None:
		for result in results:
			references.append(
				EvidenceReference(
					source=result.thought.source,
					evidence_type="DOCUMENTED_THOUGHT",
					document_id=result.thought.id,
					score=result.score,
				)
			)
			excerpts.append(result.thought.content)

	@staticmethod
	def _summary(intent: ReasoningIntent, evidence_count: int) -> str:
		noun = "source" if evidence_count == 1 else "sources"
		return f"Answer based on {evidence_count} documented {noun} for {intent.value.lower()} intent."
