"""Placeholder memory API endpoints."""

from fastapi import APIRouter


router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/memory/status")
def memory_status() -> dict[str, bool | str]:
	"""Return memory subsystem status without implementing memory."""

	return {
		"status": "memory_engine_pending",
		"short_term": False,
		"long_term": False,
		"episodic": False,
		"thought_memory": False,
	}
