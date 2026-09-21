"""Placeholder profile API endpoints."""

from fastapi import APIRouter


router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/profile")
def profile() -> dict[str, str]:
	"""Return profile subsystem status without personal information."""

	return {
		"name": "Sushant Neural Twin",
		"status": "profile_engine_pending",
	}
