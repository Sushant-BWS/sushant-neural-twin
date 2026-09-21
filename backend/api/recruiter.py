"""Evidence-based recruiter API endpoints."""

from fastapi import APIRouter

from backend.knowledge.recruiter import (
	RecruiterRequest,
	RecruiterResponse,
	RecruiterService,
)


router = APIRouter(prefix="/recruiter", tags=["recruiter"])
service = RecruiterService()


@router.get("/recruiter/status")
def recruiter_status() -> dict[str, str]:
	"""Return recruiter subsystem status."""

	return {"status": "recruiter_engine_pending"}


@router.post("/summary", response_model=RecruiterResponse)
def recruiter_summary(request: RecruiterRequest) -> RecruiterResponse:
	"""Create a recruiter summary from explicitly supplied knowledge."""

	return service.summarize(request)
