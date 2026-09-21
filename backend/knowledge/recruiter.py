"""Evidence-based recruiter summaries over supplied knowledge records."""

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from backend.knowledge.schemas import Certification, Experience, Profile, Project, Skill


class RecruiterEvidence(BaseModel):
    """A source-backed item included in a recruiter response."""

    model_config = ConfigDict(frozen=True)

    category: str
    summary: str = Field(min_length=1)
    source: str = Field(min_length=1)


class RecruiterRequest(BaseModel):
    """Explicit knowledge supplied for recruiter-mode summarization."""

    model_config = ConfigDict(extra="forbid")

    profile: Profile | None = None
    experiences: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)


class RecruiterResponse(BaseModel):
    """Evidence-based recruiter response without invented claims."""

    model_config = ConfigDict(frozen=True)

    summary: str
    evidence: list[RecruiterEvidence] = Field(default_factory=list)
    evidence_count: int = Field(ge=0)
    sufficient_evidence: bool


class RecruiterService:
    """Generate concise recruiter summaries from explicitly supplied records."""

    pending_message = "I don't have enough verified information to create a recruiter summary."

    def summarize(self, request: RecruiterRequest) -> RecruiterResponse:
        """Create a summary using only source-backed fields."""

        evidence: list[RecruiterEvidence] = []
        if request.profile and request.profile.source:
            profile_summary = request.profile.summary or request.profile.headline
            if profile_summary:
                evidence.append(
                    RecruiterEvidence(
                        category="PROFILE",
                        summary=profile_summary,
                        source=request.profile.source,
                    )
                )

        self._add_experiences(request.experiences, evidence)
        self._add_projects(request.projects, evidence)
        self._add_skills(request.skills, evidence)
        self._add_certifications(request.certifications, evidence)

        if not evidence:
            return RecruiterResponse(
                summary=self.pending_message,
                evidence_count=0,
                sufficient_evidence=False,
            )

        summary = self._build_summary(evidence)
        return RecruiterResponse(
            summary=summary,
            evidence=evidence,
            evidence_count=len(evidence),
            sufficient_evidence=True,
        )

    @staticmethod
    def _add_experiences(
        records: Iterable[Experience],
        evidence: list[RecruiterEvidence],
    ) -> None:
        for record in records:
            if record.source and record.role:
                description = record.description or record.role
                evidence.append(
                    RecruiterEvidence(
                        category="EXPERIENCE",
                        summary=description,
                        source=record.source,
                    )
                )

    @staticmethod
    def _add_projects(
        records: Iterable[Project],
        evidence: list[RecruiterEvidence],
    ) -> None:
        for record in records:
            if record.source and record.name and record.description:
                evidence.append(
                    RecruiterEvidence(
                        category="PROJECT",
                        summary=f"{record.name}: {record.description}",
                        source=record.source,
                    )
                )

    @staticmethod
    def _add_skills(
        records: Iterable[Skill],
        evidence: list[RecruiterEvidence],
    ) -> None:
        for record in records:
            if record.source and record.name:
                summary = record.proficiency or record.category or record.name
                evidence.append(
                    RecruiterEvidence(
                        category="SKILL",
                        summary=f"{record.name}: {summary}",
                        source=record.source,
                    )
                )

    @staticmethod
    def _add_certifications(
        records: Iterable[Certification],
        evidence: list[RecruiterEvidence],
    ) -> None:
        for record in records:
            if record.source and record.name:
                summary = f"{record.name} by {record.issuer}" if record.issuer else record.name
                evidence.append(
                    RecruiterEvidence(
                        category="CERTIFICATION",
                        summary=summary,
                        source=record.source,
                    )
                )

    @staticmethod
    def _build_summary(evidence: list[RecruiterEvidence]) -> str:
        categories = ", ".join(dict.fromkeys(item.category.lower() for item in evidence))
        return f"Evidence-based recruiter summary covering {categories}, supported by {len(evidence)} documented sources."
