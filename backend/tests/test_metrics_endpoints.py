"""Tests for dashboard metrics and request logs endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_requests_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/requests")
        assert res.status_code == 200
        data = res.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_metrics_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/metrics")
        assert res.status_code == 200
        data = res.json()
        assert "total_requests" in data
        assert "total_tokens" in data
        assert "total_tokens_saved" in data
        assert "models_usage" in data
        assert "content_types_breakdown" in data
        assert "time_series" in data
