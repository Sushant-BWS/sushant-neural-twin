"""Tests for the Phase 9 evidence-based reasoning engine."""

import json
import unittest

from backend.ai import (
    ReasoningEngine,
    ReasoningIntent,
    ReasoningRequest,
    SearchResult,
)
from backend.knowledge.schemas import Thought
from backend.knowledge.store import KnowledgeDocument
from backend.knowledge.thought_engine import ThoughtEngine


class ReasoningEngineTests(unittest.TestCase):
    """Verify concise evidence synthesis without private reasoning traces."""

    def setUp(self) -> None:
        self.engine = ReasoningEngine()

    @staticmethod
    def search_result(
        document_id: str,
        content: str,
        source: str,
        score: float,
    ) -> SearchResult:
        return SearchResult(
            document=KnowledgeDocument(
                id=document_id,
                content=content,
                metadata={"source": source},
            ),
            score=score,
        )

    def test_returns_insufficient_evidence_without_sources(self) -> None:
        response = self.engine.reason(
            ReasoningRequest(question="What is documented?", intent=ReasoningIntent.PROFILE)
        )

        self.assertFalse(response.sufficient_evidence)
        self.assertEqual(response.evidence_count, 0)
        self.assertIn("don't have enough verified", response.answer)
        self.assertEqual(response.evidence, [])

    def test_synthesizes_facts_and_experiences_with_references(self) -> None:
        fact = self.search_result("fact-1", "A documented skill.", "facts.json#0", 0.95)
        experience = self.search_result(
            "experience-1",
            "A documented project experience.",
            "experience.json#0",
            0.88,
        )

        response = self.engine.reason(
            ReasoningRequest(question="What is relevant?", intent=ReasoningIntent.EXPERIENCE),
            facts=[fact],
            experiences=[experience],
        )

        self.assertTrue(response.sufficient_evidence)
        self.assertEqual(response.evidence_count, 2)
        self.assertEqual(
            [reference.source for reference in response.evidence],
            ["facts.json#0", "experience.json#0"],
        )
        self.assertIn("2 documented sources", response.reasoning_summary)
        self.assertIn("A documented skill.", response.answer)

    def test_deduplicates_education_across_json_and_resume_sources(self) -> None:
        education_record = json.dumps(
            {
                "degree": "Bachelor of Computer Application",
                "institution": "IIMT University",
                "location": "Meerut, Uttar Pradesh",
                "start_year": 2021,
                "end_year": 2024,
                "achievements": [
                    "Achieved Top 1% in Academics",
                    "Participated in University Tech Events",
                ],
                "research_areas": [
                    "Cloud Computing",
                    "Cyber Security",
                    "Forensics",
                ],
            }
        )
        resume_education = (
            "Education: IIMT University Meerut, Uttar Pradesh "
            "Bachelor of Computer Application 2021-2024 "
            "Achieved Top 1% in Academics Participated in University Tech Events "
            "Researched in Cloud Computing and Cyber Security and Forensics."
        )

        response = self.engine.reason(
            ReasoningRequest(
                question="Sushant education",
                intent=ReasoningIntent.EDUCATION,
            ),
            facts=[
                self.search_result(
                    "education-json",
                    education_record,
                    "data/education/education.json",
                    0.95,
                ),
                self.search_result(
                    "resume-education",
                    resume_education,
                    "data/resume/Sushant_Resume.pdf",
                    0.90,
                ),
            ],
        )

        self.assertTrue(response.sufficient_evidence)
        self.assertEqual(response.evidence_count, 2)
        self.assertEqual(
            response.answer.count("Bachelor of Computer Application"),
            1,
        )
        self.assertIn("Achieved Top 1% in Academics", response.answer)
        self.assertNotIn("data/education/education.json", response.answer)
        self.assertNotIn("data/resume/Sushant_Resume.pdf", response.answer)
        self.assertNotIn("SUPPORTED", response.answer)
        self.assertNotIn("VERIFIED", response.answer)
        self.assertEqual(
            {reference.source for reference in response.evidence},
            {
                "data/education/education.json",
                "data/resume/Sushant_Resume.pdf",
            },
        )

    def test_resume_project_section_replaces_multiple_duplicate_records(self) -> None:
        json_serverless = (
            "Serverless Deployment on AWS: Implemented a fully serverless "
            "application using AWS Lambda, API Gateway, DynamoDB, and S3."
        )
        json_grafana = (
            "Grafana-Monitoring-Stack: Configured a Grafana monitoring "
            "stack on AWS EC2 to achieve real-time observability."
        )
        resume_projects = (
            "Project: Grafana-Monitoring-Stack. 2021 2022 configured "
            "Grafana monitoring stack on AWS EC2 with custom dashboards "
            "and alert rules. Serverless Deployment on AWS 2022-2023 "
            "implemented a scalable application with Lambda, API Gateway, "
            "DynamoDB, and S3."
        )

        response = self.engine.reason(
            ReasoningRequest(
                question="Tell me about Sushant's projects.",
                intent=ReasoningIntent.PROJECT,
            ),
            facts=[
                self.search_result(
                    "project-serverless",
                    json_serverless,
                    "data/projects/projects.json#serverless",
                    0.95,
                ),
                self.search_result(
                    "project-grafana",
                    json_grafana,
                    "data/projects/projects.json#grafana",
                    0.94,
                ),
                self.search_result(
                    "resume-projects",
                    resume_projects,
                    "data/resume/Sushant_Resume.pdf",
                    0.90,
                ),
            ],
        )

        self.assertEqual(
            response.answer.count("Grafana-Monitoring-Stack"),
            1,
        )
        self.assertEqual(
            response.answer.count("Serverless Deployment on AWS"),
            1,
        )
        self.assertEqual(response.evidence_count, 3)

    def test_integrates_documented_thoughts(self) -> None:
        thought_engine = ThoughtEngine()
        thought_engine.add_documented_thought(
            Thought(
                topic="engineering",
                statement="Prefer evidence-based decisions.",
                source="thoughts/principles.json#0",
                confidence=0.9,
                evidence=["thoughts/principles.json#0"],
            )
        )
        thought = thought_engine.search("evidence decisions")[0]

        response = self.engine.reason(
            ReasoningRequest(question="What principle is documented?", intent=ReasoningIntent.THOUGHT),
            thoughts=[thought],
        )

        self.assertEqual(response.evidence[0].evidence_type, "DOCUMENTED_THOUGHT")
        self.assertIn("Prefer evidence-based decisions.", response.answer)

    def test_ignores_evidence_without_source_reference(self) -> None:
        result = self.search_result("untraceable", "Unsupported content.", "", 0.9)

        response = self.engine.reason(
            ReasoningRequest(question="What is known?"),
            facts=[result],
        )

        self.assertFalse(response.sufficient_evidence)
        self.assertEqual(response.evidence_count, 0)

    def test_response_has_summary_not_chain_of_thought(self) -> None:
        response = self.engine.reason(
            ReasoningRequest(question="What is known?"),
        )

        self.assertTrue(hasattr(response, "reasoning_summary"))
        self.assertFalse(hasattr(response, "chain_of_thought"))
        self.assertFalse(hasattr(response, "internal_reasoning"))


if __name__ == "__main__":
    unittest.main()
