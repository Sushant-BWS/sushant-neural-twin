"""Tests for the Phase 13 evidence-based recruiter mode."""

import unittest

from fastapi.testclient import TestClient

from backend.api.recruiter import router
from backend.knowledge.recruiter import RecruiterRequest, RecruiterService
from backend.knowledge.schemas import Certification, Experience, Project, Skill
from backend.main import app


class RecruiterServiceTests(unittest.TestCase):
    """Verify recruiter summaries never invent unsupported claims."""

    def setUp(self) -> None:
        self.service = RecruiterService()

    def test_empty_input_returns_pending_response(self) -> None:
        response = self.service.summarize(RecruiterRequest())

        self.assertFalse(response.sufficient_evidence)
        self.assertEqual(response.evidence_count, 0)
        self.assertIn("enough verified information", response.summary)

    def test_summary_contains_only_source_backed_records(self) -> None:
        request = RecruiterRequest(
            experiences=[
                Experience(
                    role="Backend Engineer",
                    description="Documented backend experience.",
                    source="experience.json#0",
                ),
                Experience(role="Unsupported role", description="No source"),
            ],
            projects=[
                Project(
                    name="Project A",
                    description="Documented project work.",
                    source="projects.json#0",
                )
            ],
            skills=[Skill(name="Python", proficiency="advanced", source="skills.json#0")],
            certifications=[
                Certification(
                    name="Credential",
                    issuer="Issuer",
                    source="certifications.json#0",
                )
            ],
        )

        response = self.service.summarize(request)

        self.assertTrue(response.sufficient_evidence)
        self.assertEqual(response.evidence_count, 4)
        self.assertNotIn("Unsupported role", response.summary)
        self.assertEqual(
            {item.category for item in response.evidence},
            {"EXPERIENCE", "PROJECT", "SKILL", "CERTIFICATION"},
        )
        self.assertTrue(all(item.source for item in response.evidence))

    def test_missing_project_description_is_not_presented_as_evidence(self) -> None:
        response = self.service.summarize(
            RecruiterRequest(
                projects=[Project(name="Undocumented project", source="projects.json#0")]
            )
        )

        self.assertFalse(response.sufficient_evidence)
        self.assertEqual(response.evidence, [])


class RecruiterApiTests(unittest.TestCase):
    """Verify the recruiter API contract."""

    def test_summary_endpoint_returns_pending_without_data(self) -> None:
        client = TestClient(app)

        response = client.post("/api/recruiter/summary", json={})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["sufficient_evidence"])

    def test_summary_endpoint_accepts_structured_source_backed_data(self) -> None:
        client = TestClient(app)
        payload = {
            "skills": [
                {
                    "name": "Python",
                    "source": "skills.json#0",
                    "confidence": 0.9,
                }
            ]
        }

        response = client.post("/api/recruiter/summary", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["sufficient_evidence"])
        self.assertEqual(response.json()["evidence_count"], 1)


if __name__ == "__main__":
    unittest.main()
