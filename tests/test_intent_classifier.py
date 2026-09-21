"""Tests for the Phase 11 interpretable intent classifier."""

import unittest

from backend.ml import Intent, IntentExample, RuleBasedIntentClassifier


class IntentClassifierTests(unittest.TestCase):
    """Verify routing rules and baseline evaluation behavior."""

    def setUp(self) -> None:
        self.classifier = RuleBasedIntentClassifier()

    def test_classifies_required_intents(self) -> None:
        examples = [
            ("Tell me about my profile", Intent.PROFILE),
            ("What employment experience do I have?", Intent.EXPERIENCE),
            ("Which projects have I built?", Intent.PROJECT),
            ("What are my strongest skills?", Intent.SKILL),
            ("Where did I study?", Intent.EDUCATION),
            ("What certifications do I have?", Intent.CERTIFICATION),
            ("What principles do I believe?", Intent.THOUGHT),
            ("How do I make engineering decisions?", Intent.DECISION),
            ("What is my career timeline?", Intent.CAREER),
            ("How should a recruiter view my background?", Intent.RECRUITER),
        ]

        for text, expected in examples:
            with self.subTest(text=text):
                prediction = self.classifier.classify(text)
                self.assertEqual(prediction.intent, expected)
                self.assertGreater(prediction.score, 0)
                self.assertTrue(prediction.matched_terms)

    def test_uses_general_for_empty_or_unmatched_questions(self) -> None:
        self.assertEqual(self.classifier.classify("").intent, Intent.GENERAL)
        self.assertEqual(
            self.classifier.classify("Tell me something unrelated").intent,
            Intent.GENERAL,
        )
        self.assertEqual(self.classifier.classify("").score, 0.0)

    def test_handles_plural_forms(self) -> None:
        self.assertEqual(self.classifier.classify("What certifications exist?").intent, Intent.CERTIFICATION)
        self.assertEqual(self.classifier.classify("What decisions have I made?").intent, Intent.DECISION)
        self.assertEqual(self.classifier.classify("What technologies do I know?").intent, Intent.SKILL)

    def test_evaluates_labeled_examples(self) -> None:
        examples = [
            IntentExample(text="What are my skills?", expected=Intent.SKILL),
            IntentExample(text="What projects did I build?", expected=Intent.PROJECT),
            IntentExample(text="Where did I study?", expected=Intent.EDUCATION),
            IntentExample(text="What certifications do I have?", expected=Intent.CERTIFICATION),
        ]

        evaluation = self.classifier.evaluate(examples)

        self.assertEqual(evaluation.total, 4)
        self.assertEqual(evaluation.correct, 4)
        self.assertEqual(evaluation.accuracy, 1.0)

    def test_prediction_is_bounded(self) -> None:
        prediction = self.classifier.classify("What are my project skills?")

        self.assertGreaterEqual(prediction.score, 0)
        self.assertLessEqual(prediction.score, 1)


if __name__ == "__main__":
    unittest.main()
