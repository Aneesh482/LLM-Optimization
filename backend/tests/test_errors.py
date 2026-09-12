"""Tests for error handling edge cases."""

import pytest
from unittest.mock import AsyncMock, patch

from app.providers.base import LLMResponse


@pytest.mark.asyncio
async def test_no_api_key_returns_503(client):
    """If no Gemini key is set, /chat/completions should return 503."""
    # Reset the provider singleton so it re-initializes
    with patch("app.api.routes._provider", None):
        with patch("app.providers.gemini.settings") as mock_settings:
            mock_settings.gemini_api_key = ""

            resp = await client.post(
                "/api/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )

    assert resp.status_code == 503
    assert "GEMINI_API_KEY" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_request_logged_on_error(client):
    """Even failed requests should be persisted with status=error."""
    with patch("app.api.routes._provider") as mock_prov:
        mock_prov.generate = AsyncMock(side_effect=RuntimeError("boom"))

        with patch("app.api.routes.log_request", new_callable=AsyncMock) as mock_log:
            resp = await client.post(
                "/api/v1/chat/completions",
                json={
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )

            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args.kwargs
            assert call_kwargs["status"] == "error"
            assert "boom" in call_kwargs["error_message"]

    assert resp.status_code == 500
