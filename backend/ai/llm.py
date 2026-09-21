"""Provider-agnostic local language-model interfaces."""

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class GenerationRequest(BaseModel):
	"""Validated input for a text-generation provider."""

	model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

	prompt: str = Field(min_length=1)
	max_tokens: int = Field(default=256, ge=1, le=8192)
	temperature: float = Field(default=0.0, ge=0, le=2)


class GenerationResponse(BaseModel):
	"""Provider output with basic execution metadata."""

	text: str
	provider: str
	model: str
	finish_reason: str = "stop"


@runtime_checkable
class LLMProvider(Protocol):
	"""Interface implemented by local language-model providers."""

	provider_name: str
	model_name: str

	def generate(self, request: GenerationRequest) -> GenerationResponse:
		"""Generate text for a validated request."""
		...


class LocalDevelopmentProvider:
	"""Deterministic local provider for wiring and contract tests.

	This provider does not perform language-model inference. It intentionally
	returns a transparent placeholder until a local model adapter is selected.
	"""

	provider_name = "local-development"
	model_name = "none"

	def generate(self, request: GenerationRequest) -> GenerationResponse:
		"""Return a deterministic response without external model access."""

		return GenerationResponse(
			text=f"Local model is not configured. Received prompt: {request.prompt}",
			provider=self.provider_name,
			model=self.model_name,
		)


def generate_text(
	request: GenerationRequest,
	provider: LLMProvider | None = None,
) -> GenerationResponse:
	"""Generate through an injected provider or the local development provider."""

	selected_provider = provider or LocalDevelopmentProvider()
	return selected_provider.generate(request)
