"""Tests for the chat completions endpoint with a mocked Gemini provider."""

import pytest
from unittest.mock import AsyncMock, patch

from app.providers.base import LLMResponse


@pytest.mark.asyncio
async def test_chat_completion_success(client, mock_gemini_response):
    """A valid request with a mocked provider should return 200."""
    with patch("app.api.routes._provider") as mock_prov:
        mock_prov.generate = AsyncMock(
            return_value=LLMResponse(
                content="Recursion is when a function calls itself.",
                input_tokens=12,
                output_tokens=45,
                total_tokens=57,
                model="gemini-3.6-flash",
            )
        )

        resp = await client.post(
            "/api/v1/chat/completions",
            json={
                "model": "gemini-3.6-flash",
                "messages": [{"role": "user", "content": "Explain recursion."}],
                "temperature": 0.7,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "gemini-3.6-flash"
    assert "Recursion" in data["content"]
    assert data["usage"]["input_tokens"] == 12
    assert data["usage"]["output_tokens"] == 45
    assert data["usage"]["total_tokens"] == 57
    assert data["latency_ms"] >= 0
    assert "id" in data


@pytest.mark.asyncio
async def test_chat_completion_provider_error(client):
    """If the provider throws, we should get a 500 with the error detail."""
    with patch("app.api.routes._provider") as mock_prov:
        mock_prov.generate = AsyncMock(
            side_effect=Exception("Gemini API quota exceeded")
        )

        resp = await client.post(
            "/api/v1/chat/completions",
            json={
                "model": "gemini-3.6-flash",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert resp.status_code == 500
    assert "quota exceeded" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_completion_default_model(client):
    """When no model is specified, the default should be used."""
    with patch("app.api.routes._provider") as mock_prov:
        mock_prov.generate = AsyncMock(
            return_value=LLMResponse(
                content="hi",
                model="gemini-3.6-flash",
            )
        )

        resp = await client.post(
            "/api/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert resp.status_code == 200
    assert resp.json()["model"] == "gemini-3.6-flash"
