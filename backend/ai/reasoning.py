"""Evidence-based reasoning orchestration without private chain-of-thought."""

from collections.abc import Iterable
from enum import StrEnum
import json
import re

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
    EDUCATION = "EDUCATION"
    CERTIFICATION = "CERTIFICATION"
    THOUGHT = "THOUGHT"
    DECISION = "DECISION"
    CAREER = "CAREER"
    RECRUITER = "RECRUITER"


class ReasoningRequest(BaseModel):
    """A question and explicit intent for evidence synthesis."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    question: str = Field(min_length=1)
    intent: ReasoningIntent = ReasoningIntent.GENERAL


class EvidenceReference(BaseModel):
    """A concise reference to retrieved evidence."""

    source: str = Field(min_length=1)
    evidence_type: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    score: float | None = Field(
        default=None,
        ge=-1,
        le=1,
    )


class ReasoningResponse(BaseModel):
    """Evidence-backed answer without private reasoning traces."""

    model_config = ConfigDict(frozen=True)

    answer: str
    reasoning_summary: str
    evidence: list[EvidenceReference] = Field(
        default_factory=list
    )
    evidence_count: int = Field(ge=0)
    sufficient_evidence: bool


class ReasoningEngine:
    """
    Synthesize concise responses from explicitly retrieved evidence.

    This engine does not generate private chain-of-thought.
    It only transforms retrieved personal knowledge into
    readable, evidence-backed answers.
    """

    def reason(
        self,
        request: ReasoningRequest,
        facts: Iterable[SearchResult] = (),
        experiences: Iterable[SearchResult] = (),
        thoughts: Iterable[ThoughtSearchResult] = (),
    ) -> ReasoningResponse:
        """Create a readable answer from explicitly retrieved evidence."""

        references: list[EvidenceReference] = []
        excerpts: list[str] = []

        # ---------------------------------------------------------
        # FACT / KNOWLEDGE EVIDENCE
        # ---------------------------------------------------------

        self._collect_search_results(
            facts,
            "FACT",
            references,
            excerpts,
            request.intent,
        )

        # ---------------------------------------------------------
        # EXPERIENCE EVIDENCE
        # ---------------------------------------------------------

        self._collect_search_results(
            experiences,
            "EXPERIENCE",
            references,
            excerpts,
            request.intent,
        )

        # ---------------------------------------------------------
        # DOCUMENTED THOUGHT EVIDENCE
        # ---------------------------------------------------------

        self._collect_thoughts(
            thoughts,
            references,
            excerpts,
        )

        # ---------------------------------------------------------
        # NO EVIDENCE
        # ---------------------------------------------------------

        if not references:
            return ReasoningResponse(
                answer=(
                    "I don't have enough verified "
                    "information to answer that."
                ),
                reasoning_summary=(
                    "No retrieved evidence was provided."
                ),
                evidence_count=0,
                sufficient_evidence=False,
            )

        # ---------------------------------------------------------
        # BUILD ANSWER
        # ---------------------------------------------------------

        evidence_count = len(references)

        answer = self._build_answer(
            excerpts,
            request.intent,
        )

        summary = self._summary(
            request.intent,
            evidence_count,
        )

        return ReasoningResponse(
            answer=answer,
            reasoning_summary=summary,
            evidence=references,
            evidence_count=evidence_count,
            sufficient_evidence=True,
        )

    # =========================================================
    # SEARCH RESULT COLLECTION
    # =========================================================

    @classmethod
    def _collect_search_results(
        cls,
        results: Iterable[SearchResult],
        evidence_type: str,
        references: list[EvidenceReference],
        excerpts: list[str],
        intent: ReasoningIntent,
    ) -> None:
        """Collect searchable evidence and convert records to text."""

        for result in results:
            source = str(
                result.document.metadata.get(
                    "source",
                    "",
                )
            ).strip()

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

            readable_parts = cls._humanize_content(
                result.document.content,
                intent,
            )

            excerpts.extend(
                part
                for part in readable_parts
                if part
            )

    # =========================================================
    # THOUGHT COLLECTION
    # =========================================================

    @staticmethod
    def _collect_thoughts(
        results: Iterable[ThoughtSearchResult],
        references: list[EvidenceReference],
        excerpts: list[str],
    ) -> None:
        """Collect documented thoughts using their original statements."""

        for result in results:
            references.append(
                EvidenceReference(
                    source=result.thought.source,
                    evidence_type="DOCUMENTED_THOUGHT",
                    document_id=result.thought.id,
                    score=result.score,
                )
            )

            content = result.thought.content.strip()

            if content:
                excerpts.append(content)

    # =========================================================
    # JSON HUMANIZATION
    # =========================================================

    @staticmethod
    def _humanize_content(
        content: str,
        intent: ReasoningIntent,
    ) -> list[str]:
        """
        Convert a JSON knowledge record into human-readable
        evidence items.

        Intent-specific record detection happens before generic
        collection handling. This prevents fields such as
        "achievements" inside an education record from replacing
        the actual education information.
        """

        raw = content.strip()

        if not raw:
            return []

        # ---------------------------------------------------------
        # Try JSON
        # ---------------------------------------------------------

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return [raw]

        # ---------------------------------------------------------
        # JSON LIST
        # ---------------------------------------------------------

        if isinstance(data, list):
            results: list[str] = []

            for item in data:
                humanized = ReasoningEngine._humanize_object(
                    item,
                    intent,
                )

                if humanized:
                    results.append(humanized)

            return results

        # ---------------------------------------------------------
        # JSON DICT
        # ---------------------------------------------------------

        if isinstance(data, dict):

            # =====================================================
            # IMPORTANT EDUCATION FIX
            # =====================================================
            #
            # Education records may contain:
            #
            # {
            #   "achievements": [...],
            #   "degree": "...",
            #   "institution": "...",
            #   "location": "...",
            #   "start_year": 2021,
            #   "end_year": 2024
            # }
            #
            # We must process the complete education record first.
            # Otherwise the generic "achievements" collection below
            # would incorrectly become the answer.
            #
            if intent is ReasoningIntent.EDUCATION:
                education_fields = {
                    "degree",
                    "institution",
                    "field_of_study",
                    "specialization",
                    "start_year",
                    "end_year",
                    "location",
                    "research_areas",
                }

                if any(
                    field in data
                    for field in education_fields
                ):
                    humanized = (
                        ReasoningEngine._humanize_object(
                            data,
                            intent,
                        )
                    )

                    if humanized:
                        return [humanized]

            # =====================================================
            # PROFILE FIX
            # =====================================================

            if intent is ReasoningIntent.PROFILE:
                profile_fields = {
                    "summary",
                    "headline",
                    "name",
                    "profile",
                }

                if any(
                    field in data
                    for field in profile_fields
                ):
                    humanized = (
                        ReasoningEngine._humanize_object(
                            data,
                            intent,
                        )
                    )

                    if humanized:
                        return [humanized]

            # =====================================================
            # PROJECT FIX
            # =====================================================

            if intent is ReasoningIntent.PROJECT:
                project_fields = {
                    "name",
                    "title",
                    "description",
                    "technologies",
                    "responsibilities",
                    "outcomes",
                }

                if any(
                    field in data
                    for field in project_fields
                ):
                    humanized = (
                        ReasoningEngine._humanize_object(
                            data,
                            intent,
                        )
                    )

                    if humanized:
                        return [humanized]

            # =====================================================
            # EXPERIENCE FIX
            # =====================================================

            if intent is ReasoningIntent.EXPERIENCE:
                experience_fields = {
                    "organization",
                    "company",
                    "role",
                    "title",
                    "description",
                    "responsibilities",
                }

                if any(
                    field in data
                    for field in experience_fields
                ):
                    humanized = (
                        ReasoningEngine._humanize_object(
                            data,
                            intent,
                        )
                    )

                    if humanized:
                        return [humanized]

            # =====================================================
            # CERTIFICATION FIX
            # =====================================================

            if intent is ReasoningIntent.CERTIFICATION:
                certification_fields = {
                    "name",
                    "title",
                    "issuer",
                    "credential_id",
                }

                if any(
                    field in data
                    for field in certification_fields
                ):
                    humanized = (
                        ReasoningEngine._humanize_object(
                            data,
                            intent,
                        )
                    )

                    if humanized:
                        return [humanized]

            # ---------------------------------------------------------
            # Generic collection handling
            # ---------------------------------------------------------

            collection_keys = (
                "skills",
                "projects",
                "experiences",
                "experience",
                "education",
                "certifications",
                "achievements",
                "thoughts",
                "decisions",
                "career",
                "career_events",
            )

            for key in collection_keys:

                value = data.get(key)

                if isinstance(value, list):

                    results: list[str] = []

                    for item in value:
                        humanized = (
                            ReasoningEngine._humanize_object(
                                item,
                                intent,
                            )
                        )

                        if humanized:
                            results.append(
                                humanized
                            )

                    if results:
                        return results

            # ---------------------------------------------------------
            # Normal object
            # ---------------------------------------------------------

            humanized = (
                ReasoningEngine._humanize_object(
                    data,
                    intent,
                )
            )

            return (
                [humanized]
                if humanized
                else []
            )

        # ---------------------------------------------------------
        # Primitive value
        # ---------------------------------------------------------

        return [str(data)]

    # =========================================================
    # OBJECT HUMANIZATION
    # =========================================================

    @staticmethod
    def _humanize_object(
        data: object,
        intent: ReasoningIntent,
    ) -> str:
        """Extract useful descriptive fields without inventing content."""

        if not isinstance(data, dict):
            return str(data)

        # =====================================================
        # THOUGHT
        # =====================================================

        if intent is ReasoningIntent.THOUGHT:

            statement = data.get("statement")

            if (
                isinstance(statement, str)
                and statement.strip()
            ):
                return statement.strip()

            core_belief = data.get("core_belief")

            if (
                isinstance(core_belief, str)
                and core_belief.strip()
            ):
                return core_belief.strip()

            mindset = data.get("mindset")

            if (
                isinstance(mindset, str)
                and mindset.strip()
            ):
                return mindset.strip()

        # =====================================================
        # PROJECT
        # =====================================================

        if intent is ReasoningIntent.PROJECT:

            name = (
                data.get("name")
                or data.get("title")
            )

            description = data.get("description")

            if (
                isinstance(name, str)
                and isinstance(description, str)
                and name.strip()
                and description.strip()
            ):
                return (
                    f"{name.strip()}: "
                    f"{description.strip()}"
                )

            if (
                isinstance(description, str)
                and description.strip()
            ):
                return description.strip()

            if (
                isinstance(name, str)
                and name.strip()
            ):
                return name.strip()

        # =====================================================
        # EXPERIENCE
        # =====================================================

        if intent is ReasoningIntent.EXPERIENCE:

            organization = (
                data.get("organization")
                or data.get("company")
            )

            role = (
                data.get("role")
                or data.get("title")
            )

            description = data.get("description")

            parts: list[str] = []

            if (
                isinstance(role, str)
                and role.strip()
            ):
                parts.append(role.strip())

            if (
                isinstance(organization, str)
                and organization.strip()
            ):
                parts.append(
                    f"at {organization.strip()}"
                )

            result = " ".join(parts)

            if (
                isinstance(description, str)
                and description.strip()
            ):
                if result:
                    result += (
                        f". {description.strip()}"
                    )
                else:
                    result = description.strip()

            if result:
                return result

        # =====================================================
        # SKILL
        # =====================================================

        if intent is ReasoningIntent.SKILL:

            name = (
                data.get("name")
                or data.get("skill")
                or data.get("technology")
            )

            category = data.get("category")
            proficiency = data.get("proficiency")
            years = data.get("years_of_experience")

            parts: list[str] = []

            if (
                isinstance(name, str)
                and name.strip()
            ):
                parts.append(name.strip())

            if (
                isinstance(category, str)
                and category.strip()
            ):
                parts.append(
                    f"({category.strip()})"
                )

            if (
                isinstance(proficiency, str)
                and proficiency.strip()
            ):
                parts.append(
                    f"- {proficiency.strip()}"
                )

            if years is not None:
                parts.append(
                    f"- {years} years"
                )

            if parts:
                return " ".join(parts)

        # =====================================================
        # EDUCATION
        # =====================================================

        if intent is ReasoningIntent.EDUCATION:

            degree = data.get("degree")
            field = data.get("field_of_study")
            institution = data.get("institution")
            location = data.get("location")
            start_year = data.get("start_year")
            end_year = data.get("end_year")
            achievements = data.get("achievements")
            research_areas = data.get("research_areas")

            parts: list[str] = []

            if (
                isinstance(degree, str)
                and degree.strip()
            ):
                parts.append(
                    degree.strip()
                )

            if (
                isinstance(field, str)
                and field.strip()
            ):
                parts.append(
                    f"in {field.strip()}"
                )

            if (
                isinstance(institution, str)
                and institution.strip()
            ):
                parts.append(
                    f"from {institution.strip()}"
                )

            if (
                isinstance(location, str)
                and location.strip()
            ):
                parts.append(
                    f"in {location.strip()}"
                )

            if parts:
                summary = " ".join(parts)

                if start_year and end_year:
                    summary += f" ({start_year}-{end_year})"

                if isinstance(achievements, list):
                    achievement_items = [
                        str(item).strip()
                        for item in achievements
                        if str(item).strip()
                    ]
                    if achievement_items:
                        summary += (
                            ". Academic achievements include "
                            + "; ".join(achievement_items)
                        )

                if isinstance(research_areas, list):
                    research_items = [
                        str(item).strip()
                        for item in research_areas
                        if str(item).strip()
                    ]
                    if research_items:
                        summary += (
                            ". Research areas include "
                            + ", ".join(research_items)
                        )

                return summary.rstrip(" .") + "."

        # =====================================================
        # CERTIFICATION
        # =====================================================

        if intent is ReasoningIntent.CERTIFICATION:

            name = (
                data.get("name")
                or data.get("title")
            )

            issuer = data.get("issuer")

            if (
                isinstance(name, str)
                and isinstance(issuer, str)
                and name.strip()
                and issuer.strip()
            ):
                return (
                    f"{name.strip()} "
                    f"— issued by "
                    f"{issuer.strip()}"
                )

            if (
                isinstance(name, str)
                and name.strip()
            ):
                return name.strip()

        # =====================================================
        # DECISION
        # =====================================================

        if intent is ReasoningIntent.DECISION:

            statement = data.get("statement")
            description = data.get("description")
            title = data.get("title")

            if (
                isinstance(statement, str)
                and statement.strip()
            ):
                return statement.strip()

            if (
                isinstance(description, str)
                and description.strip()
            ):
                return description.strip()

            if (
                isinstance(title, str)
                and title.strip()
            ):
                return title.strip()

        # =====================================================
        # CAREER
        # =====================================================

        if intent is ReasoningIntent.CAREER:

            goal = data.get("goal")
            description = data.get("description")
            statement = data.get("statement")
            title = data.get("title")

            if (
                isinstance(goal, str)
                and goal.strip()
            ):
                return goal.strip()

            if (
                isinstance(description, str)
                and description.strip()
            ):
                return description.strip()

            if (
                isinstance(statement, str)
                and statement.strip()
            ):
                return statement.strip()

            if (
                isinstance(title, str)
                and title.strip()
            ):
                return title.strip()

        # =====================================================
        # RECRUITER
        # =====================================================

        if intent is ReasoningIntent.RECRUITER:

            summary = data.get("summary")
            headline = data.get("headline")
            description = data.get("description")
            title = data.get("title")
            name = data.get("name")

            for value in (
                summary,
                headline,
                description,
                title,
                name,
            ):
                if (
                    isinstance(value, str)
                    and value.strip()
                ):
                    return value.strip()

        # =====================================================
        # PROFILE / GENERAL FALLBACK
        # =====================================================

        preferred_fields = (
            "summary",
            "headline",
            "description",
            "statement",
            "title",
            "name",
        )

        for field in preferred_fields:

            value = data.get(field)

            if (
                isinstance(value, str)
                and value.strip()
            ):
                return value.strip()

        # =====================================================
        # SAFE STRING FALLBACK
        # =====================================================

        ignored_fields = {
            "id",
            "source",
            "source_document",
            "confidence",
            "created_at",
            "updated_at",
        }

        strings: list[str] = []

        for key, value in data.items():

            if key in ignored_fields:
                continue

            if (
                isinstance(value, str)
                and value.strip()
            ):
                strings.append(
                    value.strip()
                )

        return ". ".join(strings[:3])

    # =========================================================
    # BUILD FINAL ANSWER
    # =========================================================

    @staticmethod
    def _build_answer(
        excerpts: list[str],
        intent: ReasoningIntent,
    ) -> str:
        """
        Build a concise answer while preserving evidence
        boundaries.

        Every retrieved evidence item becomes an independent
        sentence. This is important because the hallucination
        guard verifies claims independently.
        """

        cleaned = ReasoningEngine._deduplicate_excerpts(
            excerpts,
            intent,
        )

        if not cleaned:
            return (
                "I don't have enough verified "
                "information to answer that."
            )

        # -----------------------------------------------------
        # Intent-specific answer limits.
        # -----------------------------------------------------

        if intent is ReasoningIntent.SKILL:
            maximum_items = 10

        elif intent is ReasoningIntent.PROJECT:
            maximum_items = 5

        elif intent is ReasoningIntent.EXPERIENCE:
            maximum_items = 5

        elif intent is ReasoningIntent.CERTIFICATION:
            maximum_items = 8

        elif intent is ReasoningIntent.EDUCATION:
            maximum_items = 5

        elif intent in {
            ReasoningIntent.THOUGHT,
            ReasoningIntent.DECISION,
        }:
            maximum_items = 5

        else:
            maximum_items = 5

        return " ".join(
            cleaned[:maximum_items]
        )

    @staticmethod
    def _deduplicate_excerpts(
        excerpts: list[str],
        intent: ReasoningIntent,
    ) -> list[str]:
        """Collapse repeated facts from overlapping sources for the answer only."""

        cleaned: list[str] = []

        for excerpt in excerpts:
            text = " ".join(excerpt.split()).strip()
            text = re.sub(
                r"^(?:education|resume|profile|skills?)\s*:\s*",
                "",
                text,
                flags=re.IGNORECASE,
            )
            text = re.sub(
                r"\bdata[\\/]\S+",
                "",
                text,
                flags=re.IGNORECASE,
            ).strip()

            if not text:
                continue

            candidate_tokens = set(
                re.findall(r"[a-z0-9]+", text.lower())
            )
            duplicate_indices: list[int] = []

            for index, existing in enumerate(cleaned):
                existing_tokens = set(
                    re.findall(r"[a-z0-9]+", existing.lower())
                )
                smaller_count = min(
                    len(candidate_tokens),
                    len(existing_tokens),
                )
                overlap = len(candidate_tokens & existing_tokens)
                containment = overlap / smaller_count if smaller_count else 0

                same_education_record = (
                    intent is ReasoningIntent.EDUCATION
                    and {"bachelor", "computer", "application"}
                    <= candidate_tokens & existing_tokens
                    and {"iimt", "university"}
                    <= candidate_tokens & existing_tokens
                )

                shared_tokens = candidate_tokens & existing_tokens
                same_project_record = (
                    intent is ReasoningIntent.PROJECT
                    and len(shared_tokens) >= 5
                    and containment >= 0.62
                )

                if (
                    containment >= 0.82
                    or same_education_record
                    or same_project_record
                ):
                    duplicate_indices.append(index)

            if not duplicate_indices:
                cleaned.append(text)
                continue

            def excerpt_quality(value: str) -> int:
                return (
                    len(re.findall(r"[a-z0-9]+", value.lower()))
                    + 2 * value.count(".")
                )

            best_existing_index = max(
                duplicate_indices,
                key=lambda index: excerpt_quality(cleaned[index]),
            )
            best_existing_quality = excerpt_quality(
                cleaned[best_existing_index]
            )

            if excerpt_quality(text) > best_existing_quality:
                keep_index = min(duplicate_indices)
                cleaned[keep_index] = text
            else:
                keep_index = best_existing_index

            for index in sorted(duplicate_indices, reverse=True):
                if index != keep_index:
                    del cleaned[index]

        return [
            text if text[-1] in ".!?" else f"{text}."
            for text in cleaned
        ]

    # =========================================================
    # REASONING SUMMARY
    # =========================================================

    @staticmethod
    def _summary(
        intent: ReasoningIntent,
        evidence_count: int,
    ) -> str:
        """Create a transparent evidence summary."""

        noun = (
            "source"
            if evidence_count == 1
            else "sources"
        )

        return (
            f"Answer based on "
            f"{evidence_count} documented "
            f"{noun} for "
            f"{intent.value.lower()} intent."
        )