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
		Intent.PROFILE: ("profile", "about me", "who am i", "summary", "background"),
		Intent.EXPERIENCE: ("experience", "worked", "employment", "role", "responsibilit"),
		Intent.PROJECT: ("project", "built", "developed", "portfolio", "implementation"),
		Intent.SKILL: ("skill", "technology", "technologies", "proficiency", "expertise"),
		Intent.EDUCATION: ("education", "degree", "university", "school", "study"),
		Intent.CERTIFICATION: ("certification", "certified", "credential", "license"),
		Intent.THOUGHT: ("thought", "principle", "believe", "learning", "opinion"),
		Intent.DECISION: ("decision", "choose", "tradeoff", "criteria", "prefer"),
		Intent.CAREER: ("career", "timeline", "career path", "goal", "growth"),
		Intent.RECRUITER: ("recruiter", "hire", "candidate", "technical strengths", "resume"),
	}

	def classify(self, text: str) -> IntentPrediction:
		"""Return the highest-scoring intent or GENERAL when no rule matches."""

		normalized = " ".join(text.strip().lower().split())
		if not normalized:
			return IntentPrediction(intent=Intent.GENERAL, score=0.0)

		tokens = set(self._token_pattern.findall(normalized))
		scored: list[tuple[float, int, Intent, list[str]]] = []
		for priority, (intent, terms) in enumerate(self._rules.items()):
			matched = [term for term in terms if self._matches(term, normalized, tokens)]
			if not matched:
				continue
			weighted_score = sum(2 if " " in term else 1 for term in matched)
			score = min(1.0, weighted_score / 3)
			if intent is Intent.RECRUITER and any(
				term in {"recruiter", "hire", "candidate", "resume"}
				for term in matched
			):
				score = min(1.0, score + 0.2)
			scored.append((score, -priority, intent, matched))

		if not scored:
			return IntentPrediction(intent=Intent.GENERAL, score=0.0)
		score, _, intent, matched = max(scored)
		return IntentPrediction(intent=intent, score=score, matched_terms=matched)

	def evaluate(self, examples: Iterable[IntentExample]) -> IntentEvaluation:
		"""Measure exact-label accuracy on a supplied labeled dataset."""

		example_list = list(examples)
		correct = sum(self.classify(example.text).intent is example.expected for example in example_list)
		total = len(example_list)
		return IntentEvaluation(
			total=total,
			correct=correct,
			accuracy=correct / total if total else 0.0,
		)

	def _matches(self, term: str, normalized: str, tokens: set[str]) -> bool:
		if " " in term:
			return term in normalized
		return any(token == term or token.startswith(term) for token in tokens)
