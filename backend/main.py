"""FastAPI application entry point for the Sushant Neural Twin."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from backend.api import chat, memory, profile, recruiter
from backend.config import settings
from backend.observability import (
    ObservabilityMiddleware,
    configure_logging,
    metrics,
)
from backend.security import SecurityMiddleware


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

configure_logging()

FRONTEND_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "frontend"
)


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Backend for the Sushant Neural Twin "
        "personal AI assistant."
    ),
    debug=settings.DEBUG,
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------
#
# Local frontend:
#   http://127.0.0.1:5500
#   http://localhost:5500
#   http://127.0.0.1:8765
#   http://localhost:8765
#
# Backend:
#   http://127.0.0.1:8000
#
# This allows the browser frontend to communicate
# with the FastAPI backend during local development.
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        *settings.cors_origins,
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8765",
        "http://localhost:8765",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Security middleware
# ---------------------------------------------------------

app.add_middleware(
    SecurityMiddleware,
    configured_settings=settings,
)


# ---------------------------------------------------------
# Observability middleware
# ---------------------------------------------------------

app.add_middleware(
    ObservabilityMiddleware,
)


# ---------------------------------------------------------
# API routers
# ---------------------------------------------------------

app.include_router(
    chat.router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    profile.router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    memory.router,
    prefix=settings.API_PREFIX,
)

app.include_router(
    recruiter.router,
    prefix=settings.API_PREFIX,
)

app.mount(
    "/frontend",
    StaticFiles(directory=FRONTEND_DIRECTORY),
    name="frontend",
)


# ---------------------------------------------------------
# System endpoints
# ---------------------------------------------------------

@app.get(
    "/",
    tags=["system"],
    include_in_schema=False,
)
def root() -> FileResponse:
    """Serve the existing Neural Twin frontend."""

    return FileResponse(
        FRONTEND_DIRECTORY / "pages" / "index.html",
        media_type="text/html",
    )


@app.get(
    "/health",
    tags=["system"],
)
def health() -> dict[str, str]:
    """Report backend health."""

    return {
        "status": "healthy",
    }


@app.get(
    "/ready",
    tags=["system"],
)
def readiness() -> dict[str, object]:
    """Report whether the application is ready."""

    return {
        "status": "ready",
        "checks": {
            "configuration": "ok",
        },
    }


# ---------------------------------------------------------
# Metrics endpoint
# ---------------------------------------------------------

@app.get(
    "/metrics",
    response_class=PlainTextResponse,
    tags=["system"],
)
def metrics_endpoint() -> str:
    """
    Expose minimal Prometheus-style metrics.

    No request content or personal information is exposed.
    """

    snapshot = metrics.snapshot()

    lines = [
        (
            "sushant_neural_twin_requests_total "
            f"{snapshot.requests_total}"
        ),
        (
            "sushant_neural_twin_errors_total "
            f"{snapshot.errors_total}"
        ),
        (
            "sushant_neural_twin_in_flight "
            f"{snapshot.in_flight}"
        ),
        (
            "sushant_neural_twin_average_latency_ms "
            f"{snapshot.average_latency_ms}"
        ),
    ]

    lines.extend(
        (
            'sushant_neural_twin_http_status_total'
            f'{{code="{code}"}} {count}'
        )
        for code, count in sorted(
            snapshot.status_codes.items()
        )
    )

    return "\n".join(lines) + "\n"