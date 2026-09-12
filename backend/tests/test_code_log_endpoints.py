"""Integration tests for Code and Log compression endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_compress_code_endpoint(client: AsyncClient):
    code = """
import os

class DataProcessor:
    def process(self, items: list) -> int:
        count = 0
        for x in items:
            count += len(str(x))
        return count
"""
    payload = {
        "content": code,
        "options": {"skeleton_only": True},
    }

    res = await client.post("/api/v1/compress/code", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["content_type"] == "code"
    assert "class DataProcessor:" in data["compressed_content"]
    assert "def process(self, items: list) -> int:" in data["compressed_content"]


@pytest.mark.asyncio
async def test_compress_logs_endpoint(client: AsyncClient):
    logs = "\n".join([
        f"2026-09-09T10:00:{i:02d} INFO GET /status 200" for i in range(25)
    ] + ["2026-09-09T10:00:30 ERROR Critical failure: OutOfMemoryError"])

    payload = {
        "content": logs,
        "options": {"repeat_threshold": 3},
    }

    res = await client.post("/api/v1/compress/logs", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["content_type"] == "logs"
    assert data["compression_ratio"] < 1.0
    assert "ERROR Critical failure" in data["compressed_content"]


@pytest.mark.asyncio
async def test_general_compress_auto_routes_code_and_logs(client: AsyncClient):
    # Auto-detect python code
    code = "import sys\ndef run():\n    return sys.version"
    res_code = await client.post("/api/v1/compress", json={"content": code})
    assert res_code.status_code == 200
    assert res_code.json()["content_type"] == "code"

    # Auto-detect logs
    logs = "\n".join([f"2026-09-09T10:{i:02d}:00 INFO Server heartbeat {i}" for i in range(15)])
    res_logs = await client.post("/api/v1/compress", json={"content": logs})
    assert res_logs.status_code == 200
    assert res_logs.json()["content_type"] == "logs"
