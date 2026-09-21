"""Synthetic, non-personal evaluation cases for Phase 16."""

from backend.ml import Intent, IntentExample

FACTUAL_CASES = [
    ("Python is a programming language.", "Python is a programming language."),
    ("A vector index returns ranked documents.", "A vector index returns ranked documents."),
    ("The unsupported answer is unknown.", "The unsupported answer is verified."),
]

RETRIEVAL_CASES = [
    ({"doc-python"}, ["doc-python", "doc-cloud"]),
    ({"doc-memory"}, ["doc-reasoning"]),
    ({"doc-project"}, ["doc-project"]),
]

INTENT_CASES = [
    IntentExample(text="What are the documented skills?", expected=Intent.SKILL),
    IntentExample(text="Which projects were built?", expected=Intent.PROJECT),
    IntentExample(text="What education is documented?", expected=Intent.EDUCATION),
    IntentExample(text="What certifications exist?", expected=Intent.CERTIFICATION),
]

CONSISTENT_OUTPUTS = [
    "Evidence-backed response.",
    " evidence-backed   response. ",
    "Evidence-backed response.",
]
