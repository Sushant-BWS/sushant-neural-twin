"""Tests for the Phase 19 observability foundation."""

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.main import app
from backend.observability import MetricsRegistry, metrics


class ObservabilityTests(unittest.TestCase):
    """Verify metrics, readiness, structured request metadata, and errors."""

    def setUp(self) -> None:
        metrics.reset()

    def test_readiness_endpoint_reports_configuration(self) -> None:
        response = TestClient(app).get("/ready")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ready", "checks": {"configuration": "ok"}})

    def test_request_duration_header_and_metrics_are_recorded(self) -> None:
        client = TestClient(app)

        response = client.get("/health")
        snapshot = metrics.snapshot()

        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Request-Duration-Ms", response.headers)
        self.assertEqual(snapshot.requests_total, 1)
        self.assertEqual(snapshot.status_codes["200"], 1)
        self.assertEqual(snapshot.paths["/health"], 1)
        self.assertGreaterEqual(snapshot.average_latency_ms, 0)

    def test_metrics_endpoint_exposes_safe_operational_values(self) -> None:
        client = TestClient(app)
        client.get("/health")

        response = client.get("/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertIn("sushant_neural_twin_requests_total", response.text)
        self.assertIn("sushant_neural_twin_http_status_total{code=\"200\"}", response.text)
        self.assertNotIn("Authorization", response.text)
        self.assertNotIn("message", response.text)

    def test_registry_tracks_errors_without_content(self) -> None:
        registry = MetricsRegistry()
        registry.record_error()
        registry.start_request()
        registry.finish_request("/private", 500, 12.5)

        snapshot = registry.snapshot()

        self.assertEqual(snapshot.errors_total, 2)
        self.assertEqual(snapshot.requests_total, 1)
        self.assertEqual(snapshot.average_latency_ms, 12.5)
        self.assertEqual(snapshot.paths, {"/private": 1})

    def test_registry_reset_clears_all_values(self) -> None:
        registry = MetricsRegistry()
        registry.start_request()
        registry.finish_request("/health", 200, 1.0)
        registry.reset()

        snapshot = registry.snapshot()

        self.assertEqual(snapshot.requests_total, 0)
        self.assertEqual(snapshot.errors_total, 0)
        self.assertEqual(snapshot.paths, {})


if __name__ == "__main__":
    unittest.main()
