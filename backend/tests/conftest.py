"""Shared test fixtures."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.database import engine, Base


@pytest.fixture(autouse=True)
async def setup_db():
    """Create a fresh in-memory DB for every test."""
    # Override to in-memory SQLite for tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Async test client that talks to the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_gemini_response():
    """A realistic mock of a Gemini SDK response object."""
    usage = MagicMock()
    usage.prompt_token_count = 12
    usage.candidates_token_count = 45

    response = MagicMock()
    response.text = "Recursion is when a function calls itself to solve a smaller sub-problem."
    response.usage_metadata = usage
    return response
