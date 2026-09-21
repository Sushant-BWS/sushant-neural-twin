"""Reusable Pydantic schemas for structured personal knowledge."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeRecord(BaseModel):
    """Common provenance and confidence metadata for knowledge records."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = ""
    source: str = ""
    confidence: float | None = Field(default=None, ge=0, le=1)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Skill(KnowledgeRecord):
    """A documented professional or technical skill."""

    name: str = ""
    category: str = ""
    proficiency: str = ""
    years_of_experience: float | None = Field(default=None, ge=0)


class Achievement(KnowledgeRecord):
    """A documented professional or academic achievement."""

    title: str = ""
    description: str = ""
    achieved_at: datetime | None = None


class Profile(KnowledgeRecord):
    """Structured professional profile information."""

    name: str = ""
    summary: str = ""
    headline: str = ""
    skills: list[Skill] = Field(default_factory=list)
    achievements: list[Achievement] = Field(default_factory=list)


class Education(KnowledgeRecord):
    """An education record."""

    institution: str = ""
    degree: str = ""
    field_of_study: str = ""
    start_date: datetime | None = None
    end_date: datetime | None = None
    description: str = ""


class Experience(KnowledgeRecord):
    """A professional experience record."""

    organization: str = ""
    role: str = ""
    start_date: datetime | None = None
    end_date: datetime | None = None
    description: str = ""
    skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)


class Project(KnowledgeRecord):
    """A documented project record."""

    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)
    start_date: datetime | None = None
    end_date: datetime | None = None


class Certification(KnowledgeRecord):
    """A certification or credential record."""

    name: str = ""
    issuer: str = ""
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    credential_id: str = ""


class Thought(KnowledgeRecord):
    """A documented thought or principle."""

    topic: str = ""
    statement: str = ""
    context: str = ""
    evidence: list[str] = Field(default_factory=list)


class DecisionPattern(KnowledgeRecord):
    """A documented decision-making pattern."""

    name: str = ""
    description: str = ""
    context: str = ""
    evidence: list[str] = Field(default_factory=list)


class CareerEvent(KnowledgeRecord):
    """A dated event in a career timeline."""

    title: str = ""
    event_type: str = ""
    description: str = ""
    occurred_at: datetime | None = None
    organization: str = ""
