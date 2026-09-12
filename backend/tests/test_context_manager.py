"""Unit tests for ContextManager (conversation rolling window, summarization, and archiving)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import async_session
from app.services.context_manager import ContextManager


@pytest.fixture
def manager() -> ContextManager:
    return ContextManager()


@pytest.fixture
async def db_session():
    async with async_session() as session:
        yield session


@pytest.mark.asyncio
async def test_context_manager_within_budget(manager: ContextManager):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    opt_msgs, metrics = await manager.optimize_context(
        messages,
        max_context_tokens=1000,
        recent_count=4,
    )

    assert len(opt_msgs) == 3
    assert metrics["summary_injected"] is False
    assert metrics["tokens_saved"] == 0
    assert metrics["compression_ratio"] == 1.0


@pytest.mark.asyncio
async def test_context_manager_rolling_window_and_summarization(
    manager: ContextManager,
    db_session: AsyncSession,
):
    # Construct a long 12-turn conversation
    messages = [{"role": "system", "content": "System instruction: Always speak concisely."}]
    for i in range(10):
        messages.append({"role": "user", "content": f"User turn question number {i+1}: Can you explain component {i+1} in detail with all its architectural patterns?"})
        messages.append({"role": "assistant", "content": f"Assistant turn answer number {i+1}: Here is the comprehensive breakdown of component {i+1} along with trade-offs and considerations."})

    opt_msgs, metrics = await manager.optimize_context(
        messages,
        max_context_tokens=100,  # Force optimization
        recent_count=2,
        preserve_system=True,
        archive_to_ccr=True,
        db=db_session,
    )

    assert metrics["summary_injected"] is True
    assert metrics["tokens_saved"] > 0
    assert metrics["compression_ratio"] < 1.0
    assert metrics["archived_context_id"] is not None
    assert metrics["archived_context_id"].startswith("ctx_")

    # Verify System message is preserved at the top
    assert opt_msgs[0]["role"] == "system"
    assert opt_msgs[0]["content"] == "System instruction: Always speak concisely."

    # Verify summary message is present
    assert any("[Context Manager - Prior History Summary]" in m["content"] for m in opt_msgs)

    # Verify recent turns are preserved at the tail
    assert opt_msgs[-1]["content"] == messages[-1]["content"]
    assert opt_msgs[-2]["content"] == messages[-2]["content"]


@pytest.mark.asyncio
async def test_context_manager_preserves_important_errors(manager: ContextManager):
    messages = [
        {"role": "system", "content": "You are a specialized debugging and reliability engineer."},
        {"role": "user", "content": "Detailed overview of microservice deployment step 1 and telemetry setup."},
        {"role": "assistant", "content": "Telemetry service configured with OpenTelemetry agents and Prometheus."},
        {"role": "user", "content": "CRITICAL ERROR: Exception: Database deadlocked at transaction 401 with lock timeout on table users."},
        {"role": "assistant", "content": "Analyzing deadlock logs: transaction 401 acquired lock on row 10 and was waiting for lock on row 20."},
        {"role": "user", "content": "Discussion on queue retry strategy and backoff intervals."},
        {"role": "assistant", "content": "Configured exponential backoff with jitter and max retries equal to 5."},
        {"role": "user", "content": "Final query: How do we prevent this deadlock?"},
    ]

    opt_msgs, metrics = await manager.optimize_context(
        messages,
        max_context_tokens=40,
        recent_count=2,
    )

    assert metrics["summary_injected"] is True
    # The critical error turn should be preserved
    assert any("CRITICAL ERROR" in m["content"] for m in opt_msgs)
