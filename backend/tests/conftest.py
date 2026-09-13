"""Shared test fixtures."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.models.database import get_session
from app.models import Base


# Create a separate test database engine (in-memory SQLite)
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
)
test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def get_test_session():
    """Test database session override."""
    async with test_session_factory() as session:
        yield session


@pytest.fixture(autouse=True)
async def setup_db():
    """Create a fresh in-memory test DB for every test."""
    # Create all tables in the test database
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Drop all tables after each test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Async test client that talks to the FastAPI app with test database."""
    # Override the database dependency to use test database
    app.dependency_overrides[get_session] = get_test_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up dependency override
    app.dependency_overrides.clear()


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
