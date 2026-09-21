"""Tests for the Phase 15 security foundation."""

import unittest

from fastapi import FastAPI
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import app
from backend.security import (
    RequestRateLimiter,
    SecurityMiddleware,
    authorize_request,
)


class SecurityTests(unittest.TestCase):
    """Verify security headers, authorization, CORS, and rate limiting."""

    def test_security_headers_are_present(self) -> None:
        response = TestClient(app).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
        self.assertIn("geolocation=()", response.headers["Permissions-Policy"])

    def test_cors_allows_configured_origin_and_methods(self) -> None:
        response = TestClient(app).options(
            "/api/chat/chat",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:3000")
        self.assertIn("POST", response.headers["access-control-allow-methods"])

    def test_cors_rejects_unconfigured_origin(self) -> None:
        response = TestClient(app).options(
            "/api/chat/chat",
            headers={
                "Origin": "http://untrusted.example",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_rate_limiter_uses_sliding_window(self) -> None:
        limiter = RequestRateLimiter(2, 60)

        self.assertTrue(limiter.allow("client", now=1))
        self.assertTrue(limiter.allow("client", now=2))
        self.assertFalse(limiter.allow("client", now=3))
        self.assertTrue(limiter.allow("client", now=62))

    def test_authorization_is_disabled_by_default(self) -> None:
        self.assertEqual(authorize_request(None, Settings()), "disabled")

    def test_authorization_requires_and_checks_bearer_token(self) -> None:
        configured = Settings(AUTH_ENABLED=True, AUTH_TOKEN="test-token")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")
        invalid = HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong-token")

        self.assertEqual(authorize_request(credentials, configured), "Bearer")
        with self.assertRaises(Exception):
            authorize_request(None, configured)
        with self.assertRaises(Exception):
            authorize_request(invalid, configured)

    def test_auth_enabled_without_token_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Settings(AUTH_ENABLED=True)

    def test_protected_middleware_rejects_missing_token(self) -> None:
        protected_app = FastAPI()
        protected_app.add_middleware(
            SecurityMiddleware,
            configured_settings=Settings(
                AUTH_ENABLED=True,
                AUTH_TOKEN="test-token",
                RATE_LIMIT_REQUESTS=10,
                RATE_LIMIT_WINDOW_SECONDS=60,
            ),
        )

        @protected_app.get("/api/private")
        def private() -> dict[str, bool]:
            return {"ok": True}

        client = TestClient(protected_app)
        self.assertEqual(client.get("/api/private").status_code, 401)
        self.assertEqual(
            client.get(
                "/api/private",
                headers={"Authorization": "Bearer test-token"},
            ).status_code,
            200,
        )


if __name__ == "__main__":
    unittest.main()
