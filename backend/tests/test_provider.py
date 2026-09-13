"""Tests for the provider abstraction and Gemini provider."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.providers.base import LLMProvider, LLMResponse
from app.providers.gemini import GeminiProvider


class TestLLMProviderInterface:
    """Verify that the base class enforces the interface."""

    def test_cannot_instantiate_base(self):
        with pytest.raises(TypeError):
            LLMProvider()

    def test_concrete_provider_must_implement_generate(self):
        class Incomplete(LLMProvider):
            async def list_models(self):
                return []

            def provider_name(self):
                return "test"

        with pytest.raises(TypeError):
            Incomplete()


class TestLLMResponse:
    """Verify the response dataclass."""

    def test_defaults(self):
        r = LLMResponse(content="hello")
        assert r.content == "hello"
        assert r.input_tokens is None
        assert r.output_tokens is None
        assert r.total_tokens is None
        assert r.model == ""

    def test_with_usage(self):
        r = LLMResponse(
            content="hi",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            model="gemini-3.6-flash",
        )
        assert r.total_tokens == 30


class TestGeminiProvider:
    """Test the Gemini provider with mocked SDK calls."""

    def test_requires_api_key(self):
        with patch("app.providers.gemini.settings") as mock_settings:
            mock_settings.gemini_api_key = ""
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                GeminiProvider(api_key="")

    def test_provider_name(self):
        with patch("app.providers.gemini.genai"):
            provider = GeminiProvider(api_key="test-key")
            assert provider.provider_name() == "gemini"

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_gemini_response):
        with patch("app.providers.gemini.genai"):
            provider = GeminiProvider(api_key="test-key")
            provider._call_gemini = AsyncMock(return_value=mock_gemini_response)

            result = await provider.generate(
                messages=[{"role": "user", "content": "Explain recursion."}],
                model="gemini-3.6-flash",
                temperature=0.7,
            )

            assert isinstance(result, LLMResponse)
            assert "Recursion" in result.content
            assert result.input_tokens == 12
            assert result.output_tokens == 45
            assert result.total_tokens == 57
            assert result.model == "gemini-3.6-flash"

    @pytest.mark.asyncio
    async def test_generate_with_system_message(self, mock_gemini_response):
        with patch("app.providers.gemini.genai"):
            provider = GeminiProvider(api_key="test-key")
            provider._call_gemini = AsyncMock(return_value=mock_gemini_response)

            result = await provider.generate(
                messages=[
                    {"role": "system", "content": "You are a helpful tutor."},
                    {"role": "user", "content": "Explain recursion."},
                ],
                model="gemini-3.6-flash",
            )

            # Verify system message was separated out
            call_kwargs = provider._call_gemini.call_args.kwargs
            assert call_kwargs["system_instruction"] == "You are a helpful tutor."
            # Only the user message should be in contents
            assert len(call_kwargs["contents"]) == 1

    @pytest.mark.asyncio
    async def test_generate_handles_missing_usage(self):
        """If Gemini returns no usage_metadata, tokens should be None."""
        response = MagicMock()
        response.text = "Hello"
        response.usage_metadata = None

        with patch("app.providers.gemini.genai"):
            provider = GeminiProvider(api_key="test-key")
            provider._call_gemini = AsyncMock(return_value=response)

            result = await provider.generate(
                messages=[{"role": "user", "content": "hi"}],
                model="gemini-3.6-flash",
            )

            assert result.input_tokens is None
            assert result.output_tokens is None
            assert result.total_tokens is None

    def test_prepare_contents_splits_system(self):
        messages = [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "bye"},
        ]
        system, contents = GeminiProvider._prepare_contents(messages)
        assert system == "Be concise."
        assert len(contents) == 3
        assert contents[0].role == "user"
        assert contents[1].role == "model"  # assistant → model
        assert contents[2].role == "user"
