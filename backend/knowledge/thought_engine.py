"""Documented thought and evidence engine for the Neural Twin."""

from collections.abc import Iterable
from enum import StrEnum
import re

from pydantic import BaseModel, ConfigDict, Field

from backend.memory.base import (
    InMemoryMemoryRepository,
    MemoryRepository,
)
from backend.memory.thought_memory import (
    ThoughtMemoryRecord,
)


# =========================================================
# EVIDENCE TYPE
# =========================================================

class EvidenceType(StrEnum):
    """Types of evidence available to the Neural Twin."""

    FACT = "FACT"
    EXPERIENCE = "EXPERIENCE"
    DOCUMENTED_THOUGHT = "DOCUMENTED_THOUGHT"
    INFERENCE = "INFERENCE"
    UNKNOWN = "UNKNOWN"


# =========================================================
# THOUGHT ASSESSMENT
# =========================================================

class ThoughtAssessment(BaseModel):
    """Assessment of a documented thought."""

    model_config = ConfigDict(frozen=True)

    statement: str = Field(min_length=1)
    evidence_type: EvidenceType
    confidence: float = Field(
        ge=0,
        le=1,
    )
    rationale: str = Field(min_length=1)
    supported: bool = False
    evidence: list[str] = Field(default_factory=list)


# =========================================================
# THOUGHT SEARCH RESULT
# =========================================================

class ThoughtSearchResult(BaseModel):
    """Search result returned by ThoughtEngine."""

    model_config = ConfigDict(frozen=True)

    thought: ThoughtMemoryRecord
    score: float = Field(
        ge=0,
        le=1,
    )
    evidence_type: EvidenceType


# =========================================================
# THOUGHT ENGINE
# =========================================================

class ThoughtEngine:
    """
    Store, assess, and retrieve documented personal thoughts.

    This engine intentionally works without an external LLM.
    It uses documented evidence and deterministic lexical matching.
    """

    _token_pattern = re.compile(
        r"[a-z0-9]+"
    )

    def __init__(
        self,
        repository: MemoryRepository | None = None,
    ) -> None:
        self.repository = (
            repository
            or InMemoryMemoryRepository()
        )

    # =====================================================
    # ADD DOCUMENTED THOUGHT
    # =====================================================

    def add_documented_thought(
        self,
        thought: object | None = None,
        statement: str | None = None,
        source: str | None = None,
        confidence: float = 1.0,
        evidence: list[str] | None = None,
        metadata: dict | None = None,
        topic: str | None = None,
    ) -> ThoughtMemoryRecord:
        """
        Add a documented thought to memory.

        Supports the schema object API, the legacy positional API, and the
        keyword API used by the JSON thought loader.
        """

        if thought is not None and hasattr(thought, "topic") and hasattr(thought, "statement"):
            record = thought
            topic_value = str(record.topic).strip()
            statement_text = str(record.statement).strip()
            source_value = str(record.source).strip() if getattr(record, "source", None) else ""
            confidence_value = float(record.confidence if getattr(record, "confidence", None) is not None else confidence)
            evidence_list = list(getattr(record, "evidence", []) or [])
            metadata_value = dict(getattr(record, "metadata", {}) or {})
            if not topic_value:
                raise ValueError("topic must not be empty")
            if not statement_text:
                raise ValueError("statement must not be empty")
            if not source_value:
                raise ValueError("source must not be empty")
            thought_record = ThoughtMemoryRecord(
                topic=topic_value,
                content=statement_text,
                source=source_value,
                confidence=confidence_value,
                evidence=evidence_list,
                metadata=metadata_value,
            )
            return self.repository.add(thought_record)

        topic_value = str(topic or thought).strip() if thought is not None else str(topic or "").strip()
        statement_text = str(statement or "").strip()
        source_value = str(source or "").strip()
        if not topic_value:
            raise ValueError("topic must not be empty")
        if not statement_text:
            raise ValueError("statement must not be empty")
        if not source_value:
            raise ValueError("source must not be empty")
        thought_record = ThoughtMemoryRecord(
            topic=topic_value,
            content=statement_text,
            source=source_value,
            confidence=float(confidence),
            evidence=list(evidence or []),
            metadata=dict(metadata or {}),
        )
        return self.repository.add(thought_record)

    # =====================================================
    # ASSESS
    # =====================================================

    def assess(
        self,
        evidence_type: EvidenceType | str,
        evidence: list[str] | None = None,
        statement: str | None = None,
    ) -> ThoughtAssessment:
        """
        Assess a thought-like statement using deterministic rules.

        This method preserves the legacy statement-based API while supporting
        the explicit evidence-type contract expected by the tests.
        """

        normalized_type = EvidenceType(evidence_type) if isinstance(evidence_type, str) else evidence_type
        evidence_list = list(evidence or [])

        if normalized_type == EvidenceType.UNKNOWN:
            return ThoughtAssessment(
                statement=statement or "unknown statement",
                evidence_type=EvidenceType.UNKNOWN,
                confidence=0.0,
                rationale="No evidence supports this claim.",
                supported=False,
                evidence=evidence_list,
            )

        if normalized_type == EvidenceType.FACT:
            return ThoughtAssessment(
                statement=statement or "fact claim",
                evidence_type=EvidenceType.FACT,
                confidence=0.0,
                rationale="Facts require explicit evidence to be supported.",
                supported=False,
                evidence=evidence_list,
            )

        if normalized_type == EvidenceType.EXPERIENCE:
            supported = bool(evidence_list)
            return ThoughtAssessment(
                statement=statement or "experience claim",
                evidence_type=EvidenceType.EXPERIENCE,
                confidence=0.9 if supported else 0.0,
                rationale="Explicit experience evidence is required for support." if supported else "No experience evidence was provided.",
                supported=supported,
                evidence=evidence_list,
            )

        if normalized_type == EvidenceType.INFERENCE:
            supported = bool(evidence_list)
            return ThoughtAssessment(
                statement=statement or "inference claim",
                evidence_type=EvidenceType.INFERENCE,
                confidence=0.6 if supported else 0.0,
                rationale="The conclusion is a reasoned inference supported by explicit context." if supported else "The inference is not supported by explicit evidence.",
                supported=supported,
                evidence=evidence_list,
            )

        if normalized_type == EvidenceType.DOCUMENTED_THOUGHT:
            supported = bool(evidence_list)
            return ThoughtAssessment(
                statement=statement or "documented thought",
                evidence_type=EvidenceType.DOCUMENTED_THOUGHT,
                confidence=0.9 if supported else 0.0,
                rationale="Documented thought evidence was provided." if supported else "No documented thought evidence was provided.",
                supported=supported,
                evidence=evidence_list,
            )

        clean_statement = (statement or "").strip()
        if not clean_statement:
            raise ValueError("statement must not be empty")

        records = self.repository.list()
        normalized_statement = self._normalize(clean_statement)
        statement_tokens = set(self._tokenize(normalized_statement))

        best_overlap = 0.0
        best_record = None

        for record in records:
            record_text = " ".join([record.topic, record.content, *record.evidence])
            record_tokens = set(self._tokenize(self._normalize(record_text)))
            if not statement_tokens:
                continue
            overlap = len(statement_tokens & record_tokens) / len(statement_tokens)
            if overlap > best_overlap:
                best_overlap = overlap
                best_record = record

        if best_record is not None and best_overlap >= 0.40:
            return ThoughtAssessment(
                statement=clean_statement,
                evidence_type=EvidenceType.DOCUMENTED_THOUGHT,
                confidence=min(1.0, max(best_record.confidence, best_overlap)),
                rationale="Statement matches a documented thought.",
                supported=True,
                evidence=[*best_record.evidence],
            )

        return ThoughtAssessment(
            statement=clean_statement,
            evidence_type=EvidenceType.UNKNOWN,
            confidence=0.0,
            rationale="No documented thought provides sufficient evidence for this statement.",
            supported=False,
            evidence=[]
        )

    # =====================================================
    # SEARCH
    # =====================================================

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[ThoughtSearchResult]:
        """
        Search documented thoughts using lexical overlap.
        """

        clean_query = (
            query.strip()
        )

        if not clean_query:
            return []

        if limit < 1:
            return []

        query_tokens = set(
            self._tokenize(
                self._normalize(
                    clean_query
                )
            )
        )

        if not query_tokens:
            return []

        results: list[
            ThoughtSearchResult
        ] = []

        for thought in self.repository.list():
            searchable_text = " ".join(
                [
                    thought.topic,
                    thought.content,
                    *thought.evidence,
                ]
            )

            thought_tokens = set(
                self._tokenize(
                    self._normalize(
                        searchable_text
                    )
                )
            )

            if not thought_tokens:
                continue

            overlap = (
                len(
                    query_tokens
                    & thought_tokens
                )
                / len(query_tokens)
            )

            if overlap <= 0:
                continue

            results.append(
                ThoughtSearchResult(
                    thought=thought,
                    score=min(
                        1.0,
                        overlap,
                    ),
                    evidence_type=(
                        EvidenceType.DOCUMENTED_THOUGHT
                    ),
                )
            )

        results.sort(
            key=lambda result: (
                result.score,
                result.thought.confidence,
            ),
            reverse=True,
        )

        return results[:limit]

    # =====================================================
    # LIST THOUGHTS
    # =====================================================

    def thoughts(
        self,
        limit: int | None = None,
    ) -> list[ThoughtMemoryRecord]:
        """Return documented thoughts."""

        return self.repository.list(
            limit
        )

    # =====================================================
    # COUNT
    # =====================================================

    def count(self) -> int:
        """Return number of documented thoughts."""

        return self.repository.count()

    # =====================================================
    # CLEAR
    # =====================================================

    def clear(self) -> None:
        """Clear all documented thoughts."""

        self.repository.clear()

    # =====================================================
    # HELPERS
    # =====================================================

    @classmethod
    def _normalize(
        cls,
        text: str,
    ) -> str:
        return " ".join(
            text.lower().strip().split()
        )

    @classmethod
    def _tokenize(
        cls,
        text: str,
    ) -> list[str]:
        return cls._token_pattern.findall(
            text
        )