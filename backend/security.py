"""Centralized security middleware and authorization helpers."""

from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
import hmac
import logging
import time

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from backend.config import Settings, settings

logger = logging.getLogger("sushant_neural_twin.security")
_bearer = HTTPBearer(auto_error=False)


class RateLimitState(BaseModel):
    """Mutable-free snapshot of rate-limit configuration."""

    requests: int
    window_seconds: int


class RequestRateLimiter:
    """Small process-local sliding-window limiter for development use."""

    def __init__(self, requests: int, window_seconds: int) -> None:
        if requests < 1 or window_seconds < 1:
            raise ValueError("rate-limit values must be at least 1")
        self.state = RateLimitState(
            requests=requests,
            window_seconds=window_seconds,
        )
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, client_id: str, now: float | None = None) -> bool:
        """Return whether the client may make another request."""

        current = now if now is not None else time.monotonic()
        timestamps = self._requests[client_id]
        cutoff = current - self.state.window_seconds
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()
        if len(timestamps) >= self.state.requests:
            return False
        timestamps.append(current)
        return True

    def reset(self) -> None:
        """Clear all local rate-limit history."""

        self._requests.clear()


def authorize_request(
    credentials: HTTPAuthorizationCredentials | None,
    configured_settings: Settings = settings,
) -> str:
    """Validate an optional configured bearer token and return its scheme."""

    if not configured_settings.AUTH_ENABLED:
        return "disabled"
    if not configured_settings.AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured.",
        )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not hmac.compare_digest(credentials.credentials, configured_settings.AUTH_TOKEN):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.scheme


class SecurityMiddleware(BaseHTTPMiddleware):
    """Apply headers, request logging, optional auth, and rate limiting."""

    def __init__(self, app: Callable[..., Awaitable[Response]], configured_settings: Settings = settings) -> None:
        super().__init__(app)
        self.configured_settings = configured_settings
        self.rate_limiter = RequestRateLimiter(
            configured_settings.RATE_LIMIT_REQUESTS,
            configured_settings.RATE_LIMIT_WINDOW_SECONDS,
        )

    async def dispatch(self, request: Request, call_next: Callable[..., Awaitable[Response]]) -> Response:
        """Process one request without logging credentials or request bodies."""

        client_id = request.client.host if request.client else "unknown"
        if not self.rate_limiter.allow(client_id):
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded."},
            )
        elif self._requires_auth(request):
            auth_header = request.headers.get("authorization", "")
            scheme, _, token = auth_header.partition(" ")
            if (
                scheme.lower() != "bearer"
                or not self.configured_settings.AUTH_TOKEN
                or not hmac.compare_digest(token, self.configured_settings.AUTH_TOKEN)
            ):
                response = JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Bearer authentication is required."},
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)

        self._add_security_headers(response)
        logger.info("request method=%s path=%s status=%s", request.method, request.url.path, response.status_code)
        return response

    def _requires_auth(self, request: Request) -> bool:
        return self.configured_settings.AUTH_ENABLED and request.url.path.startswith(
            self.configured_settings.API_PREFIX
        )

    @staticmethod
    def _add_security_headers(response: Response) -> None:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
