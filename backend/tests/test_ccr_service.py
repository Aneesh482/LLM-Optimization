"""Unit tests for CCR (Compress - Cache - Retrieve) service."""

from __future__ import annotations

import json
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import async_session
from app.services.ccr_service import ccr_service


@pytest.fixture
async def db_session():
    async with async_session() as session:
        yield session


@pytest.mark.asyncio
async def test_store_and_retrieve_context(db_session: AsyncSession):
    raw_data = [
        {"id": i, "server": "us-east", "cpu_pct": 20.0 + (i % 5), "status": "ok"}
        for i in range(30)
    ]
    raw_str = json.dumps(raw_data)

    # 1. Store
    record = await ccr_service.store_context(
        db_session,
        content=raw_str,
        content_type="json",
        description="US East server metrics",
        options={"max_representatives": 2},
    )

    assert record.context_id.startswith("ctx_")
    assert record.content_type == "json"
    assert record.original_size == len(raw_str.encode("utf-8"))
    assert record.compressed_size < record.original_size
    assert record.compression_ratio < 1.0
    assert record.estimated_tokens_saved > 0
    assert record.access_count == 0

    # 2. Get Context (Metadata & Compressed)
    fetched = await ccr_service.get_context(db_session, record.context_id)
    assert fetched is not None
    assert fetched.context_id == record.context_id
    assert fetched.access_count == 1

    # 3. Retrieve Original Verbatim Content
    orig = await ccr_service.retrieve_original(db_session, record.context_id)
    assert orig is not None
    assert orig.original_content == raw_str
    assert orig.access_count == 2


@pytest.mark.asyncio
async def test_store_auto_detect_json(db_session: AsyncSession):
    data = [{"metric": "load", "val": 0.45}, {"metric": "mem", "val": 82.1}]
    record = await ccr_service.store_context(
        db_session,
        content=json.dumps(data),
    )
    assert record.content_type == "json"
    assert record.context_id.startswith("ctx_")


@pytest.mark.asyncio
async def test_list_contexts_pagination(db_session: AsyncSession):
    for i in range(5):
        await ccr_service.store_context(
            db_session,
            content=f"Log message test line {i}",
            content_type="logs",
            description=f"Log batch {i}",
        )

    total, items = await ccr_service.list_contexts(db_session, limit=3, offset=0)
    assert total >= 5
    assert len(items) == 3

    total2, items2 = await ccr_service.list_contexts(db_session, limit=3, offset=3)
    assert len(items2) >= 2


@pytest.mark.asyncio
async def test_get_nonexistent_context(db_session: AsyncSession):
    res = await ccr_service.get_context(db_session, "ctx_nonexistent_999")
    assert res is None
