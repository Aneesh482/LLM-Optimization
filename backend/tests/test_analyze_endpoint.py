"""Tests for the /api/v1/analyze endpoint."""

import pytest


@pytest.mark.asyncio
async def test_analyze_single_message(client):
    resp = await client.post(
        "/api/v1/analyze",
        json={
            "messages": [{"role": "user", "content": "Explain recursion in Python."}],
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_messages"] == 1
    assert data["total_estimated_tokens"] >= 1
    assert data["estimation_method"] == "heuristic"
    assert len(data["messages"]) == 1
    assert data["messages"][0]["role"] == "user"


@pytest.mark.asyncio
async def test_analyze_conversation(client):
    resp = await client.post(
        "/api/v1/analyze",
        json={
            "messages": [
                {"role": "system", "content": "You are a helpful tutor."},
                {"role": "user", "content": "What is a list comprehension?"},
                {"role": "assistant", "content": "A list comprehension is a concise way to create lists in Python."},
                {"role": "user", "content": "Give me an example."},
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_messages"] == 4
    assert len(data["role_distribution"]) == 3  # system, user, assistant

    roles = {r["role"] for r in data["role_distribution"]}
    assert roles == {"system", "user", "assistant"}


@pytest.mark.asyncio
async def test_analyze_empty_messages_rejected(client):
    resp = await client.post(
        "/api/v1/analyze",
        json={"messages": []},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_analyze_large_message(client):
    large_content = "word " * 5000  # ~5000 words
    resp = await client.post(
        "/api/v1/analyze",
        json={
            "messages": [{"role": "user", "content": large_content}],
        },
    )
    assert resp.status_code == 200
    data = resp.json()

    # 5000 words * 1.3 ≈ 6500 estimated tokens
    assert data["total_estimated_tokens"] > 5000
    assert data["largest_sections"][0]["percentage_of_total"] == 100.0
