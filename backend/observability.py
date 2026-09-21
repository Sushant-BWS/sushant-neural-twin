"""Dependency-free structured logging, metrics, and request observability."""

from collections import Counter
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
import json
import logging
import time
from threading import Lock
from typing import Any

from fastapi import Request
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class MetricsSnapshot(BaseModel):
    """Serializable application metrics snapshot."""

    requests_total: int = Field(ge=0)
    errors_total: int = Field(ge=0)
    in_flight: int = Field(ge=0)
    average_latency_ms: float = Field(ge=0)
    status_codes: dict[str, int] = Field(default_factory=dict)
    paths: dict[str, int] = Field(default_factory=dict)


class MetricsRegistry:
    """Thread-safe process-local metrics registry for the current instance."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._requests_total = 0
        self._errors_total = 0
        self._in_flight = 0
        self._latency_total_ms = 0.0
        self._status_codes: Counter[str] = Counter()
        self._paths: Counter[str] = Counter()

    def start_request(self) -> None:
        """Record the start of a request."""

        with self._lock:
            self._in_flight += 1

    def finish_request(self, path: str, status_code: int, latency_ms: float) -> None:
        """Record a completed request without storing request content."""

        with self._lock:
            self._requests_total += 1
            self._in_flight = max(0, self._in_flight - 1)
            self._latency_total_ms += max(0.0, latency_ms)
            self._status_codes[str(status_code)] += 1
            self._paths[path] += 1
            if status_code >= 500:
                self._errors_total += 1

    def record_error(self) -> None:
        """Record an exception before the framework handles it."""

        with self._lock:
            self._errors_total += 1

    def snapshot(self) -> MetricsSnapshot:
        """Return a consistent metrics snapshot."""

        with self._lock:
            average = (
                self._latency_total_ms / self._requests_total
                if self._requests_total
                else 0.0
            )
            return MetricsSnapshot(
                requests_total=self._requests_total,
                errors_total=self._errors_total,
                in_flight=self._in_flight,
                average_latency_ms=round(average, 3),
                status_codes=dict(self._status_codes),
                paths=dict(self._paths),
            )

    def reset(self) -> None:
        """Clear metrics for isolated tests or local development."""

        with self._lock:
            self._requests_total = 0
            self._errors_total = 0
            self._in_flight = 0
            self._latency_total_ms = 0.0
            self._status_codes.clear()
            self._paths.clear()


metrics = MetricsRegistry()
logger = logging.getLogger("sushant_neural_twin.observability")


class JsonLogFormatter(logging.Formatter):
    """Format logs as structured JSON without sensitive request data."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize safe operational fields only."""

        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("method", "path", "status_code", "latency_ms"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, sort_keys=True)


def configure_logging() -> None:
    """Install a concise structured handler when none is configured."""

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Track request counts, errors, and latency without collecting content."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[..., Awaitable[Response]],
    ) -> Response:
        """Measure one request and re-raise unhandled exceptions."""

        started = time.perf_counter()
        metrics.start_request()
        try:
            response = await call_next(request)
        except Exception:
            metrics.record_error()
            logger.exception("unhandled request error", extra={"method": request.method, "path": request.url.path})
            raise
        latency_ms = (time.perf_counter() - started) * 1000
        metrics.finish_request(request.url.path, response.status_code, latency_ms)
        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": round(latency_ms, 3),
            },
        )
        response.headers["X-Request-Duration-Ms"] = f"{latency_ms:.3f}"
        return response
