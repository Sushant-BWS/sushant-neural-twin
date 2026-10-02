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
    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )


class ClaimVerification(BaseModel):
    """Verification result for one claim."""

    model_config = ConfigDict(frozen=True)

    claim: str = Field(min_length=1)
    status: ClaimStatus
    evidence: list[ClaimEvidence] = Field(
        default_factory=list
    )
    overlap: float = Field(
        default=0,
        ge=0,
        le=1,
    )
    rationale: str


class GuardedAnswer(BaseModel):
    """An answer after claim verification."""

    model_config = ConfigDict(frozen=True)

    answer: str
    verifications: list[ClaimVerification] = Field(
        default_factory=list
    )
    safe: bool


class HallucinationGuard:
    """
    Deterministic hallucination protection layer.

    The guard does not generate facts.

    It checks whether the answer claims are supported
    by the evidence supplied by the Neural Twin.
    """

    # ---------------------------------------------------------
    # Tokenization
    # ---------------------------------------------------------

    _token_pattern = re.compile(
        r"[a-z0-9]+"
    )

    # Sentence-like claim splitting.
    _claim_pattern = re.compile(
        r"[^.!?]+(?:[.!?]|$)"
    )

    # Very short generic words should not contribute
    # strongly to evidence matching.
    _stop_words = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "does",
        "for",
        "from",
        "has",
        "have",
        "he",
        "her",
        "his",
        "i",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "s",
        "that",
        "the",
        "their",
        "this",
        "to",
        "was",
        "were",
        "what",
        "which",
        "with",
    }

    insufficient_message = (
        "I don't have enough verified "
        "information to answer that."
    )

    # =========================================================
    # PUBLIC API
    # =========================================================

    def verify_claim(
        self,
        claim: str,
        evidence: Iterable[
            SearchResult
            | ThoughtSearchResult
            | ClaimEvidence
        ],
    ) -> ClaimVerification:
        """
        Verify one claim against supplied evidence.

        A claim is:

        VERIFIED
            when the complete claim appears directly
            in an evidence item.

        SUPPORTED
            when enough meaningful claim tokens are
            present in an evidence item.

        UNCERTAIN
            when only partial overlap exists.

        UNKNOWN
            when no meaningful evidence supports it.
        """

        normalized_claim = self._normalize_text(
            claim
        )

        if not normalized_claim:
            raise ValueError(
                "claim must not be empty"
            )

        claim_tokens = self._meaningful_tokens(
            normalized_claim
        )

        candidates = [
            self._to_claim_evidence(item)
            for item in evidence
        ]

        candidates = [
            item
            for item in candidates
            if item is not None
        ]

        if not candidates or not claim_tokens:
            return ClaimVerification(
                claim=normalized_claim,
                status=ClaimStatus.UNKNOWN,
                rationale=(
                    "No verified evidence was provided "
                    "for this claim."
                ),
            )

        best_overlap = 0.0
        best_evidence: list[ClaimEvidence] = []
        exact_match = False

        normalized_claim_lower = (
            normalized_claim.lower()
        )

        claim_without_punctuation = (
            normalized_claim_lower.rstrip(
                ".!?"
            )
        )

        # -----------------------------------------------------
        # Compare against every evidence item.
        # -----------------------------------------------------

        for candidate in candidates:

            content = self._normalize_text(
                candidate.content
            )

            if not content:
                continue

            content_lower = content.lower()

            content_tokens = self._meaningful_tokens(
                content
            )

            # -------------------------------------------------
            # Exact textual containment.
            # -------------------------------------------------

            if (
                claim_without_punctuation
                and claim_without_punctuation
                in content_lower
            ):
                exact_match = True

            # -------------------------------------------------
            # Token overlap.
            # -------------------------------------------------

            if not claim_tokens:
                overlap = 0.0
            else:
                overlap = (
                    len(
                        claim_tokens
                        & content_tokens
                    )
                    / len(claim_tokens)
                )

            if overlap > best_overlap:
                best_overlap = overlap
                best_evidence = [
                    candidate
                ]

            elif (
                overlap == best_overlap
                and overlap > 0
            ):
                best_evidence.append(
                    candidate
                )

        # -----------------------------------------------------
        # Determine status.
        # -----------------------------------------------------

        if exact_match:
            status = ClaimStatus.VERIFIED

            rationale = (
                "The claim appears directly "
                "in documented evidence."
            )

        elif best_overlap >= 0.70:
            status = ClaimStatus.SUPPORTED

            rationale = (
                "The claim has strong meaningful "
                "token overlap with documented evidence."
            )

        elif best_overlap >= 0.35:
            status = ClaimStatus.UNCERTAIN

            rationale = (
                "Evidence partially overlaps with "
                "the claim but does not sufficiently "
                "support it."
            )

        else:
            status = ClaimStatus.UNKNOWN

            rationale = (
                "No supplied evidence sufficiently "
                "supports the claim."
            )

        return ClaimVerification(
            claim=normalized_claim,
            status=status,
            evidence=best_evidence,
            overlap=best_overlap,
            rationale=rationale,
        )

    # =========================================================
    # ANSWER VERIFICATION
    # =========================================================

    def verify_answer(
        self,
        answer: str,
        evidence: Iterable[
            SearchResult
            | ThoughtSearchResult
            | ClaimEvidence
        ],
    ) -> list[ClaimVerification]:
        """
        Verify every sentence-like claim in an answer.
        """

        if not answer.strip():
            return []

        claims = [
            match.group(0).strip()
            for match in self._claim_pattern.finditer(
                answer
            )
        ]

        return [
            self.verify_claim(
                claim,
                evidence,
            )
            for claim in claims
            if claim
        ]

    # =========================================================
    # FINAL GUARD
    # =========================================================

    def guard_answer(
        self,
        answer: str,
        evidence: Iterable[
            SearchResult
            | ThoughtSearchResult
            | ClaimEvidence
        ],
    ) -> GuardedAnswer:
        """
        Return the answer only when every claim is
        sufficiently supported.

        This is the final safety boundary before the
        response reaches the API/frontend.
        """

        evidence_items = list(
            evidence
        )

        verifications = self.verify_answer(
            answer,
            evidence_items,
        )

        # -----------------------------------------------------
        # No claims
        # -----------------------------------------------------

        if not verifications:
            return GuardedAnswer(
                answer=self.insufficient_message,
                verifications=[],
                safe=False,
            )

        # -----------------------------------------------------
        # Every claim must be verified/supported.
        # -----------------------------------------------------

        safe = all(
            verification.status
            in {
                ClaimStatus.VERIFIED,
                ClaimStatus.SUPPORTED,
            }
            for verification in verifications
        )

        return GuardedAnswer(
            answer=(
                answer
                if safe
                else self.insufficient_message
            ),
            verifications=verifications,
            safe=safe,
        )

    # =========================================================
    # EVIDENCE CONVERSION
    # =========================================================

    @staticmethod
    def _to_claim_evidence(
        item: (
            SearchResult
            | ThoughtSearchResult
            | ClaimEvidence
        ),
    ) -> ClaimEvidence | None:
        """
        Convert different evidence types into one
        normalized ClaimEvidence structure.
        """

        # -----------------------------------------------------
        # Already normalized evidence
        # -----------------------------------------------------

        if isinstance(
            item,
            ClaimEvidence,
        ):
            return item

        # -----------------------------------------------------
        # Knowledge search result
        # -----------------------------------------------------

        if isinstance(
            item,
            SearchResult,
        ):
            source = str(
                item.document.metadata.get(
                    "source",
                    "",
                )
            ).strip()

            content = (
                item.document.content
                .strip()
            )

            if not source or not content:
                return None

            confidence = max(0.0, min(1.0, float(item.score)))
            return ClaimEvidence(
                source=source,
                content=content,
                evidence_type=(
                    "RETRIEVED_DOCUMENT"
                ),
                confidence=confidence,
            )

        # -----------------------------------------------------
        # Documented thought result
        # -----------------------------------------------------

        source = (
            item.thought.source
            .strip()
        )

        content = (
            item.thought.content
            .strip()
        )

        if not source or not content:
            return None

        confidence = max(0.0, min(1.0, float(item.score)))
        return ClaimEvidence(
            source=source,
            content=content,
            evidence_type=(
                "DOCUMENTED_THOUGHT"
            ),
            confidence=confidence,
        )

    # =========================================================
    # TEXT NORMALIZATION
    # =========================================================

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        """
        Normalize whitespace while preserving
        the original meaning.
        """

        return " ".join(
            value.strip().split()
        )

    # =========================================================
    # TOKEN PROCESSING
    # =========================================================

    def _meaningful_tokens(
        self,
        text: str,
    ) -> set[str]:
        """
        Extract meaningful lexical tokens.

        Stop words are removed so generic words such as
        'is', 'the', 'and', 'from' do not artificially
        increase evidence overlap.
        """

        tokens = self._token_pattern.findall(
            text.lower()
        )

        return {
            token
            for token in tokens
            if token not in self._stop_words
        }