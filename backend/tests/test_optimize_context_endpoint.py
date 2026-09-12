"""Integration tests for /api/v1/context/optimize endpoint and chat context optimization."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_optimize_context_endpoint(client: AsyncClient):
    messages = [{"role": "system", "content": "You are a helpful and experienced backend software engineer."}]
    for i in range(8):
        messages.append({
            "role": "user",
            "content": f"User question {i+1}: Could you provide a comprehensive architectural explanation of distributed systems, consensus algorithms, raft protocols, and replication strategies for component {i+1}?"
        })
        messages.append({
            "role": "assistant",
            "content": f"Assistant answer {i+1}: In distributed systems architecture {i+1}, Raft decomposes consensus into leader election, log replication, and safety. Leaders handle all client requests and synchronize followers..."
        })

    payload = {
        "messages": messages,
        "max_context_tokens": 100,
        "recent_messages_count": 2,
        "preserve_system": True,
        "archive_to_ccr": True,
    }

    response = await client.post("/api/v1/context/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "optimized_messages" in data
    assert "metrics" in data
    metrics = data["metrics"]
    assert metrics["original_message_count"] == 17
    assert metrics["optimized_message_count"] < 17
    assert metrics["summary_injected"] is True
    assert metrics["tokens_saved"] > 0
    assert metrics["archived_context_id"] is not None


@pytest.mark.asyncio
async def test_chat_completions_with_context_optimization(client: AsyncClient, mock_gemini_response):
    messages = [{"role": "system", "content": "You are a code assistant."}]
    for i in range(6):
        messages.append({"role": "user", "content": f"User question {i+1}"})
        messages.append({"role": "assistant", "content": f"Assistant response {i+1}"})

    payload = {
        "model": "gemini-3.6-flash",
        "messages": messages,
        "optimize_context": True,
        "max_context_tokens": 50,
    }

    with patch("app.providers.gemini.GeminiProvider._call_gemini", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_gemini_response
        response = await client.post("/api/v1/chat/completions", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "gemini-3.6-flash"
    assert data["content"] != ""
