"""Placeholder chat API endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator


router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
	"""Request body for the placeholder chat endpoint."""

	message: str = Field(min_length=1)

	@field_validator("message")
	@classmethod
	def validate_message(cls, value: str) -> str:
		"""Reject messages that contain only whitespace."""

		message = value.strip()
		if not message:
			raise ValueError("message must not be empty")
		return message


class ChatResponse(BaseModel):
	"""Response body for the placeholder chat endpoint."""

	message: str
	status: str


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
	"""Return a placeholder until the Personal AI Core is implemented."""

	return ChatResponse(
		message=(
			"Chat engine is not implemented yet. This endpoint is ready "
			"for the future Personal AI Core."
		),
		status="placeholder",
	)
