"""FastAPI application entry point for the backend foundation."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from backend.api import chat, memory, profile, recruiter
from backend.config import settings
from backend.observability import ObservabilityMiddleware, configure_logging, metrics
from backend.security import SecurityMiddleware

configure_logging()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend foundation for the Sushant Neural Twin project.",
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(SecurityMiddleware, configured_settings=settings)
app.add_middleware(ObservabilityMiddleware)

app.include_router(chat.router, prefix=settings.API_PREFIX)
app.include_router(profile.router, prefix=settings.API_PREFIX)
app.include_router(memory.router, prefix=settings.API_PREFIX)
app.include_router(recruiter.router, prefix=settings.API_PREFIX)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    """Return basic application metadata."""

    return {
        "name": settings.APP_NAME,
        "status": "online",
        "version": settings.APP_VERSION,
    }


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Report backend health."""

    return {"status": "healthy"}


@app.get("/ready", tags=["system"])
def readiness() -> dict[str, object]:
    """Report whether the application is ready to receive traffic."""

    return {"status": "ready", "checks": {"configuration": "ok"}}


@app.get("/metrics", response_class=PlainTextResponse, tags=["system"])
def metrics_endpoint() -> str:
    """Expose minimal text metrics without request or personal content."""

    snapshot = metrics.snapshot()
    lines = [
        f"sushant_neural_twin_requests_total {snapshot.requests_total}",
        f"sushant_neural_twin_errors_total {snapshot.errors_total}",
        f"sushant_neural_twin_in_flight {snapshot.in_flight}",
        f"sushant_neural_twin_average_latency_ms {snapshot.average_latency_ms}",
    ]
    lines.extend(
        f'sushant_neural_twin_http_status_total{{code="{code}"}} {count}'
        for code, count in sorted(snapshot.status_codes.items())
    )
    return "\n".join(lines) + "\n"
