"""Configuration and fixtures for API integration tests."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.main import app
from app.models.collection import Collection


@pytest_asyncio.fixture
async def api_client(session: AsyncSession) -> AsyncClient:
    """Create async test client for API tests."""
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_test_collection(session: AsyncSession) -> Collection:
    """Create a test collection for API tests."""
    collection = Collection(
        name="api-test-collection",
        embedding_model="nomic-embed-text",
        embedding_dimension=768,
    )
    session.add(collection)
    await session.flush()
    return collection
