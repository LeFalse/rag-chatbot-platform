"""Configuration and fixtures for API integration tests."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.main import app
from app.models.collection import Collection
from app.services.cache.redis_client import RedisClient


@pytest_asyncio.fixture
async def mock_redis_client() -> AsyncMock:
    """Create a mock Redis client for testing."""
    mock_client = AsyncMock(spec=RedisClient)
    mock_client.ping = AsyncMock(return_value=True)
    mock_client.get = AsyncMock(return_value=None)
    mock_client.set = AsyncMock(return_value=True)
    mock_client.get_json = AsyncMock(return_value=None)
    mock_client.set_json = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=1)
    mock_client.exists = AsyncMock(return_value=False)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.scan_keys = AsyncMock(return_value=[])
    mock_client.client = AsyncMock()
    return mock_client


@pytest_asyncio.fixture
async def api_client(session: AsyncSession, mock_redis_client: AsyncMock) -> AsyncClient:
    """Create async test client for API tests."""
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    # Create async mock that returns the mock_redis_client
    async def mock_get_redis():
        return mock_redis_client

    # Mock the get_redis_client function
    with patch(
        "app.api.routes.chat.get_redis_client",
        new=mock_get_redis
    ), patch(
        "app.api.routes.documents.get_redis_client",
        new=mock_get_redis
    ):
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
