"""Deterministic claim verification and hallucination protection."""

from collections.abc import Iterable
from enum import StrEnum
import re

from pydantic import BaseModel, ConfigDict, Field

from backend.ai.retrieval import SearchResult
from backend.knowledge.thought_engine import ThoughtSearchResult


class ClaimStatus(StrEnum):
	"""Support status assigned to a response claim."""

	VERIFIED = "VERIFIED"
	SUPPORTED = "SUPPORTED"
	UNCERTAIN = "UNCERTAIN"
	UNKNOWN = "UNKNOWN"


class ClaimEvidence(BaseModel):
	"""Evidence excerpt used to verify one claim."""

	model_config = ConfigDict(frozen=True)

	source: str = Field(min_length=1)
	content: str = Field(min_length=1)
	evidence_type: str = Field(min_length=1)
	confidence: float | None = Field(default=None, ge=0, le=1)


class ClaimVerification(BaseModel):
	"""Verification result for one claim, without hidden reasoning traces."""

	model_config = ConfigDict(frozen=True)

	claim: str = Field(min_length=1)
	status: ClaimStatus
	evidence: list[ClaimEvidence] = Field(default_factory=list)
	overlap: float = Field(default=0, ge=0, le=1)
	rationale: str


class GuardedAnswer(BaseModel):
	"""An answer after claim verification."""

	model_config = ConfigDict(frozen=True)

	answer: str
	verifications: list[ClaimVerification] = Field(default_factory=list)
	safe: bool


class HallucinationGuard:
	"""Verify claims against explicit evidence using transparent lexical rules."""

	_token_pattern = re.compile(r"[a-z0-9]+")
	_claim_pattern = re.compile(r"[^.!?]+(?:[.!?]|$)")
	insufficient_message = "I don't have enough verified information to answer that."

	def verify_claim(
		self,
		claim: str,
		evidence: Iterable[SearchResult | ThoughtSearchResult | ClaimEvidence],
	) -> ClaimVerification:
		"""Classify one claim against supplied source-backed evidence."""

		normalized_claim = " ".join(claim.strip().split())
		if not normalized_claim:
			raise ValueError("claim must not be empty")

		claim_tokens = set(self._token_pattern.findall(normalized_claim.lower()))
		candidates = [self._to_claim_evidence(item) for item in evidence]
		candidates = [item for item in candidates if item is not None]
		if not candidates or not claim_tokens:
			return ClaimVerification(
				claim=normalized_claim,
				status=ClaimStatus.UNKNOWN,
				rationale="No verified evidence was provided for this claim.",
			)

		best_overlap = 0.0
		best_evidence: list[ClaimEvidence] = []
		exact_match = False
		for candidate in candidates:
			content = " ".join(candidate.content.strip().split())
			content_tokens = set(self._token_pattern.findall(content.lower()))
			overlap = len(claim_tokens & content_tokens) / len(claim_tokens)
			if overlap > best_overlap:
				best_overlap = overlap
				best_evidence = [candidate]
			elif overlap == best_overlap and overlap > 0:
				best_evidence.append(candidate)
			if normalized_claim.lower().rstrip(".!?") in content.lower():
				exact_match = True

		if exact_match:
			status = ClaimStatus.VERIFIED
			rationale = "The claim appears directly in documented evidence."
		elif best_overlap >= 0.6:
			status = ClaimStatus.SUPPORTED
			rationale = "The claim has substantial token overlap with documented evidence."
		elif best_overlap > 0:
			status = ClaimStatus.UNCERTAIN
			rationale = "Evidence overlaps with the claim but does not sufficiently support it."
		else:
			status = ClaimStatus.UNKNOWN
			rationale = "No supplied evidence supports the claim."

		return ClaimVerification(
			claim=normalized_claim,
			status=status,
			evidence=best_evidence,
			overlap=best_overlap,
			rationale=rationale,
		)

	def verify_answer(
		self,
		answer: str,
		evidence: Iterable[SearchResult | ThoughtSearchResult | ClaimEvidence],
	) -> list[ClaimVerification]:
		"""Verify each sentence-like claim in an answer."""

		claims = [match.group(0).strip() for match in self._claim_pattern.finditer(answer)]
		return [self.verify_claim(claim, evidence) for claim in claims if claim]

	def guard_answer(
		self,
		answer: str,
		evidence: Iterable[SearchResult | ThoughtSearchResult | ClaimEvidence],
	) -> GuardedAnswer:
		"""Return the answer only when every claim is supported or verified."""

		evidence_items = list(evidence)
		verifications = self.verify_answer(answer, evidence_items)
		safe = bool(verifications) and all(
			verification.status in {ClaimStatus.VERIFIED, ClaimStatus.SUPPORTED}
			for verification in verifications
		)
		return GuardedAnswer(
			answer=answer if safe else self.insufficient_message,
			verifications=verifications,
			safe=safe,
		)

	@staticmethod
	def _to_claim_evidence(
		item: SearchResult | ThoughtSearchResult | ClaimEvidence,
	) -> ClaimEvidence | None:
		if isinstance(item, ClaimEvidence):
			return item
		if isinstance(item, SearchResult):
			source = str(item.document.metadata.get("source", "")).strip()
			if not source:
				return None
			return ClaimEvidence(
				source=source,
				content=item.document.content,
				evidence_type="RETRIEVED_DOCUMENT",
				confidence=item.score,
			)
		return ClaimEvidence(
			source=item.thought.source,
			content=item.thought.content,
			evidence_type="DOCUMENTED_THOUGHT",
			confidence=item.score,
		)
