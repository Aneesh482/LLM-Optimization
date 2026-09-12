"""Tests for chat completion request validation."""

import pytest


@pytest.mark.asyncio
async def test_empty_messages_rejected(client):
    """Sending an empty messages list should return 422."""
    resp = await client.post(
        "/api/v1/chat/completions",
        json={"model": "gemini-3.6-flash", "messages": []},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_missing_content_rejected(client):
    """A message with no content field should return 422."""
    resp = await client.post(
        "/api/v1/chat/completions",
        json={
            "model": "gemini-3.6-flash",
            "messages": [{"role": "user"}],
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_temperature_rejected(client):
    """Temperature outside 0-2 should be rejected."""
    resp = await client.post(
        "/api/v1/chat/completions",
        json={
            "model": "gemini-3.6-flash",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 5.0,
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_missing_messages_rejected(client):
    """Request body without messages should return 422."""
    resp = await client.post(
        "/api/v1/chat/completions",
        json={"model": "gemini-3.6-flash"},
    )
    assert resp.status_code == 422
