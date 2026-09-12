"""Integration tests for CCR Context API endpoints."""

from __future__ import annotations

import json
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ccr_endpoints_full_lifecycle(client: AsyncClient):
    records = [
        {"tx_id": f"tx_{i}", "amount": 100.0 + i * 5, "currency": "USD", "status": "completed"}
        for i in range(25)
    ]
    records.append({"tx_id": "tx_err", "amount": 0.0, "currency": "USD", "status": "FAILED", "error": "InsufficientFunds"})

    # 1. POST /api/v1/context/store
    store_payload = {
        "content": records,
        "description": "Payment transactions batch",
        "options": {
            "max_representatives": 2,
            "max_anomalies": 2,
        },
    }

    store_res = await client.post("/api/v1/context/store", json=store_payload)
    assert store_res.status_code == 200
    stored = store_res.json()

    context_id = stored["context_id"]
    assert context_id.startswith("ctx_")
    assert stored["retrieval_reference"] == f"[CCR:{context_id}]"
    assert stored["content_type"] == "json"
    assert stored["compression_ratio"] < 1.0
    assert stored["estimated_tokens_saved"] > 0
    assert "schema" in stored["compressed_content"]

    # 2. GET /api/v1/context/{context_id}
    detail_res = await client.get(f"/api/v1/context/{context_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["context_id"] == context_id
    assert detail["description"] == "Payment transactions batch"
    assert detail["access_count"] == 1

    # 3. POST /api/v1/context/{context_id}/retrieve
    retrieve_res = await client.post(f"/api/v1/context/{context_id}/retrieve")
    assert retrieve_res.status_code == 200
    retrieved = retrieve_res.json()
    assert retrieved["context_id"] == context_id
    assert retrieved["access_count"] == 2

    # Verbatim original content verified
    parsed_orig = json.loads(retrieved["original_content"])
    assert len(parsed_orig) == 26

    # 4. GET /api/v1/contexts
    list_res = await client.get("/api/v1/contexts?limit=10&offset=0")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1
    assert any(item["context_id"] == context_id for item in list_data["items"])


@pytest.mark.asyncio
async def test_get_nonexistent_context_returns_404(client: AsyncClient):
    res = await client.get("/api/v1/context/ctx_does_not_exist_404")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_retrieve_nonexistent_context_returns_404(client: AsyncClient):
    res = await client.post("/api/v1/context/ctx_does_not_exist_404/retrieve")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()
