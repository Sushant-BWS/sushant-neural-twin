"""Interpretable baseline classifier for personal-knowledge questions."""

from collections.abc import Iterable, Mapping
from enum import StrEnum
import re

from pydantic import BaseModel, ConfigDict, Field


class Intent(StrEnum):
    """Supported question intents."""

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
    GENERAL = "GENERAL"


class IntentPrediction(BaseModel):
    """Interpretable result from the baseline classifier."""

    model_config = ConfigDict(frozen=True)

    intent: Intent
    score: float = Field(ge=0, le=1)
    matched_terms: list[str] = Field(default_factory=list)


class IntentExample(BaseModel):
    """A labeled example for lightweight evaluation."""

    text: str = Field(min_length=1)
    expected: Intent


class IntentEvaluation(BaseModel):
    """Aggregate result for labeled intent examples."""

    total: int = Field(ge=0)
    correct: int = Field(ge=0)
    accuracy: float = Field(ge=0, le=1)


class RuleBasedIntentClassifier:
    """Classify questions with transparent keyword rules."""

    _token_pattern = re.compile(r"[a-z0-9]+")

    _rules: Mapping[Intent, tuple[str, ...]] = {
        Intent.PROFILE: (
            "profile",
            "about me",
            "who am i",
            "summary",
            "background",
            "introduce",
            "introduction",
        ),

        Intent.EXPERIENCE: (
            "experience",
            "worked",
            "work experience",
            "employment",
            "job",
            "jobs",
            "role",
            "roles",
            "responsibilit",
            "company",
            "companies",
        ),

        Intent.PROJECT: (
            "project",
            "projects",
            "built",
            "developed",
            "develop",
            "portfolio",
            "implementation",
            "created",
            "create",
        ),

        Intent.SKILL: (
            "skill",
            "skills",
            "technology",
            "technologies",
            "tech stack",
            "proficiency",
            "expertise",
            "technical skills",
            "tools",
        ),

        Intent.EDUCATION: (
            "education",
            "degree",
            "university",
            "college",
            "school",
            "study",
            "studied",
            "graduation",
            "graduate",
            "graduated",
            "bca",
            "bachelor",
            "bachelors",
            "institute",
            "institution",
            "academic",
            "academics",
            "qualification",
            "qualifications",
            "educational",
        ),

        Intent.CERTIFICATION: (
            "certification",
            "certifications",
            "certified",
            "certificate",
            "certificates",
            "credential",
            "credentials",
            "license",
            "licenses",
            "az-900",
            "azure fundamentals",
        ),

        Intent.THOUGHT: (
            "thought",
            "thoughts",
            "principle",
            "principles",
            "believe",
            "belief",
            "learning",
            "opinion",
            "mindset",
            "philosophy",
        ),

        Intent.DECISION: (
            "decision",
            "decisions",
            "choose",
            "chosen",
            "choice",
            "tradeoff",
            "tradeoffs",
            "criteria",
            "prefer",
            "preference",
            "why did",
            "why choose",
        ),

        Intent.CAREER: (
            "career",
            "career path",
            "timeline",
            "goal",
            "goals",
            "growth",
            "future",
            "ambition",
            "career goal",
        ),

        Intent.RECRUITER: (
            "recruiter",
            "recruiters",
            "hire",
            "hiring",
            "candidate",
            "candidates",
            "technical strengths",
            "resume",
            "cv",
            "job profile",
        ),
    }

    def classify(self, text: str) -> IntentPrediction:
        """Return the highest-scoring intent or GENERAL when no rule matches."""

        normalized = " ".join(text.strip().lower().split())

        if not normalized:
            return IntentPrediction(
                intent=Intent.GENERAL,
                score=0.0,
            )

        tokens = set(self._token_pattern.findall(normalized))

        scored: list[tuple[float, int, Intent, list[str]]] = []

        for priority, (intent, terms) in enumerate(self._rules.items()):
            matched = [
                term
                for term in terms
                if self._matches(term, normalized, tokens)
            ]

            if not matched:
                continue

            weighted_score = sum(
                2 if " " in term else 1
                for term in matched
            )

            score = min(1.0, weighted_score / 3)

            # Recruiter-specific questions receive a small boost.
            if intent is Intent.RECRUITER and any(
                term in {
                    "recruiter",
                    "recruiters",
                    "hire",
                    "hiring",
                    "candidate",
                    "candidates",
                    "resume",
                    "cv",
                }
                for term in matched
            ):
                score = min(1.0, score + 0.2)

            # Education-specific wording such as
            # "which college", "where did he graduate",
            # or "what degree" should strongly map to EDUCATION.
            if intent is Intent.EDUCATION and any(
                term in {
                    "college",
                    "university",
                    "graduation",
                    "graduate",
                    "graduated",
                    "degree",
                    "bca",
                    "bachelor",
                    "educational",
                    "education",
                    "academic",
                }
                for term in matched
            ):
                score = min(1.0, score + 0.25)

            scored.append(
                (
                    score,
                    -priority,
                    intent,
                    matched,
                )
            )

        if not scored:
            return IntentPrediction(
                intent=Intent.GENERAL,
                score=0.0,
            )

        score, _, intent, matched = max(scored)

        return IntentPrediction(
            intent=intent,
            score=score,
            matched_terms=matched,
        )

    def evaluate(
        self,
        examples: Iterable[IntentExample],
    ) -> IntentEvaluation:
        """Measure exact-label accuracy on a supplied labeled dataset."""

        example_list = list(examples)

        correct = sum(
            self.classify(example.text).intent is example.expected
            for example in example_list
        )

        total = len(example_list)

        return IntentEvaluation(
            total=total,
            correct=correct,
            accuracy=correct / total if total else 0.0,
        )

    def _matches(
        self,
        term: str,
        normalized: str,
        tokens: set[str],
    ) -> bool:
        """Check whether a rule term is present in the question."""

        if " " in term:
            return term in normalized

        return any(
            token == term or token.startswith(term)
            for token in tokens
        )