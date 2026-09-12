"""Unit tests for Gemini Provider Context Caching abstraction."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.providers.gemini import GeminiProvider
from app.providers.base import CacheHandle


@pytest.fixture
def provider() -> GeminiProvider:
    return GeminiProvider(api_key="test_dummy_key_123")


@pytest.mark.asyncio
async def test_create_context_cache(provider: GeminiProvider):
    mock_cache = MagicMock()
    mock_cache.name = "cachedContents/cache_12345"
    mock_cache.model = "gemini-3.6-flash"
    mock_cache.display_name = "DocCache"
    mock_cache.expire_time = "2026-09-09T23:59:59Z"
    
    usage = MagicMock()
    usage.total_token_count = 5400
    mock_cache.usage_metadata = usage

    with patch.object(provider._client.aio.caches, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_cache
        handle = await provider.create_context_cache(
            messages=[{"role": "user", "content": "Large documentation body..."}],
            model="gemini-3.6-flash",
            ttl_seconds=600,
            display_name="DocCache",
        )

        assert isinstance(handle, CacheHandle)
        assert handle.name == "cachedContents/cache_12345"
        assert handle.cached_tokens == 5400


@pytest.mark.asyncio
async def test_generate_with_cached_content_returns_cached_tokens(provider: GeminiProvider):
    mock_response = MagicMock()
    mock_response.text = "Here is the answer based on cached docs."
    
    usage = MagicMock()
    usage.prompt_token_count = 15
    usage.candidates_token_count = 35
    usage.cached_content_token_count = 4200
    mock_response.usage_metadata = usage

    with patch.object(provider, "_call_gemini", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_response
        res = await provider.generate(
            messages=[{"role": "user", "content": "Query"}],
            model="gemini-3.6-flash",
            cached_content="cachedContents/cache_12345",
        )

        assert res.cached_tokens == 4200
        assert res.input_tokens == 15
        assert res.output_tokens == 35
        assert res.content == "Here is the answer based on cached docs."


@pytest.mark.asyncio
async def test_delete_context_cache(provider: GeminiProvider):
    with patch.object(provider._client.aio.caches, "delete", new_callable=AsyncMock) as mock_del:
        mock_del.return_value = None
        success = await provider.delete_context_cache(cache_name="cachedContents/cache_12345")
        assert success is True
