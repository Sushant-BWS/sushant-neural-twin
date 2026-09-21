"""Tests for the Phase 6 local LLM provider boundary."""

import unittest

from backend.ai import (
    GenerationRequest,
    GenerationResponse,
    LLMProvider,
    LocalDevelopmentProvider,
    generate_text,
)


class LLMProviderTests(unittest.TestCase):
    """Verify provider injection and request validation."""

    def test_local_provider_satisfies_contract(self) -> None:
        provider = LocalDevelopmentProvider()

        self.assertIsInstance(provider, LLMProvider)
        response = provider.generate(GenerationRequest(prompt="hello"))

        self.assertIsInstance(response, GenerationResponse)
        self.assertEqual(response.provider, "local-development")
        self.assertEqual(response.model, "none")
        self.assertIn("hello", response.text)

    def test_default_generation_uses_local_provider(self) -> None:
        response = generate_text(GenerationRequest(prompt="hello"))

        self.assertEqual(response.provider, "local-development")
        self.assertEqual(response.finish_reason, "stop")

    def test_provider_can_be_injected(self) -> None:
        class StubProvider:
            provider_name = "stub"
            model_name = "test-model"

            def generate(self, request: GenerationRequest) -> GenerationResponse:
                return GenerationResponse(
                    text=request.prompt.upper(),
                    provider=self.provider_name,
                    model=self.model_name,
                )

        response = generate_text(GenerationRequest(prompt="hello"), StubProvider())

        self.assertEqual(response.text, "HELLO")
        self.assertEqual(response.provider, "stub")
        self.assertEqual(response.model, "test-model")

    def test_generation_request_rejects_invalid_values(self) -> None:
        with self.assertRaises(ValueError):
            GenerationRequest(prompt="   ")
        with self.assertRaises(ValueError):
            GenerationRequest(prompt="hello", max_tokens=0)
        with self.assertRaises(ValueError):
            GenerationRequest(prompt="hello", temperature=2.1)


if __name__ == "__main__":
    unittest.main()
