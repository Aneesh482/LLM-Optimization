"""Integration tests for Provider Caching and Hierarchy Status endpoints."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from app.providers.base import CacheHandle


@pytest.mark.asyncio
async def test_cache_hierarchy_status_endpoint(client: AsyncClient):
    res = await client.get("/api/v1/cache/status")
    assert res.status_code == 200
    data = res.json()

    assert "tier_1_in_memory_gateway_cache" in data
    assert "tier_2_ccr_sqlite_storage" in data
    assert "tier_3_provider_context_caching" in data


@pytest.mark.asyncio
async def test_create_and_list_provider_cache_endpoints(client: AsyncClient):
    mock_handle = CacheHandle(
        name="cachedContents/ctx_mock_999",
        model="gemini-3.6-flash",
        display_name="Test Cache",
        expire_time="2026-09-09T23:59:59Z",
        cached_tokens=3200,
    )

    with patch("app.providers.gemini.GeminiProvider.create_context_cache", new_callable=AsyncMock) as mock_create, \
         patch("app.providers.gemini.GeminiProvider.list_context_caches", new_callable=AsyncMock) as mock_list, \
         patch("app.providers.gemini.GeminiProvider.get_context_cache", new_callable=AsyncMock) as mock_get, \
         patch("app.providers.gemini.GeminiProvider.delete_context_cache", new_callable=AsyncMock) as mock_delete:

        mock_create.return_value = mock_handle
        mock_list.return_value = [mock_handle]
        mock_get.return_value = mock_handle
        mock_delete.return_value = True

        # 1. Create cache
        create_payload = {
            "model": "gemini-3.6-flash",
            "ttl_seconds": 600,
            "display_name": "Test Cache",
            "messages": [{"role": "user", "content": "Large cached text block"}],
        }
        res_create = await client.post("/api/v1/cache/provider/create", json=create_payload)
        assert res_create.status_code == 200
        created = res_create.json()
        assert created["name"] == "cachedContents/ctx_mock_999"
        assert created["cached_tokens"] == 3200

        # 2. List caches
        res_list = await client.get("/api/v1/cache/provider")
        assert res_list.status_code == 200
        listed = res_list.json()
        assert listed["total"] == 1

        # 3. Get single cache
        res_get = await client.get(f"/api/v1/cache/provider/{created['name']}")
        assert res_get.status_code == 200
        assert res_get.json()["name"] == created["name"]

        # 4. Delete cache
        res_del = await client.delete(f"/api/v1/cache/provider/{created['name']}")
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "deleted"
