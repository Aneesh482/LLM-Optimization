"""Integration tests for compression endpoints."""

from __future__ import annotations

import json
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_compress_json_endpoint(client: AsyncClient):
    records = [{"id": i, "val": i * 1.5, "status": "ok"} for i in range(25)]
    records.append({"id": 999, "val": 9999.9, "status": "CRITICAL_ERROR"})

    payload = {
        "content": json.dumps(records),
        "content_type": "json",
        "options": {
            "max_representatives": 3,
            "max_anomalies": 2,
        },
    }

    response = await client.post("/api/v1/compress", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["content_type"] == "json"
    assert data["original_size"] > 0
    assert data["compressed_size"] < data["original_size"]
    assert data["compression_ratio"] < 1.0
    assert data["estimated_tokens_saved"] > 0

    parsed = json.loads(data["compressed_content"])
    assert "schema" in parsed
    assert "representative_records" in parsed
    assert "anomalies" in parsed


@pytest.mark.asyncio
async def test_compress_json_explicit_endpoint(client: AsyncClient):
    records = [{"code": f"A{i}", "score": i} for i in range(20)]
    payload = {"content": json.dumps(records)}

    response = await client.post("/api/v1/compress/json", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["content_type"] == "json"
    assert data["compression_ratio"] < 1.0


@pytest.mark.asyncio
async def test_compress_auto_detection_endpoint(client: AsyncClient):
    # Without providing content_type, router should auto-detect JSON
    records = [{"event": "login", "user": f"u_{i}", "ts": 1700000000 + i} for i in range(15)]
    payload = {"content": json.dumps(records)}

    response = await client.post("/api/v1/compress", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "json"


@pytest.mark.asyncio
async def test_compress_empty_content_validation(client: AsyncClient):
    response = await client.post("/api/v1/compress", json={"content": ""})
    assert response.status_code == 422  # Pydantic validation min_length=1
