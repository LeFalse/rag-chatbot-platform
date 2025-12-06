"""Configuration and fixtures for API integration tests."""

import shutil
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.main import app
from app.models.collection import Collection
from app.models.document import Document
from app.models.chunk import Chunk
from app.services.cache.redis_client import RedisClient

UPLOAD_DIR = Path("uploads")


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
    # Track collections before test to cleanup upload folders after
    result = await session.execute(select(Collection.id))
    existing_collection_ids = {row[0] for row in result.fetchall()}

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session

    # Create async mock that returns the mock_redis_client
    async def mock_get_redis():
        return mock_redis_client

    # Create a mock AsyncSessionLocal that returns the test session
    # This is needed because /ask endpoint uses AsyncSessionLocal() directly
    @asynccontextmanager
    async def mock_async_session_local():
        yield session

    # Mock the get_redis_client function and AsyncSessionLocal
    with patch(
        "app.api.routes.chat.get_redis_client",
        new=mock_get_redis
    ), patch(
        "app.api.routes.chat.AsyncSessionLocal",
        new=mock_async_session_local
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

    # Cleanup: Delete upload folders created during test
    # (DB records are rolled back automatically by session fixture)
    result = await session.execute(select(Collection.id))
    all_collection_ids = {row[0] for row in result.fetchall()}
    new_collection_ids = all_collection_ids - existing_collection_ids

    for collection_id in new_collection_ids:
        folder_path = UPLOAD_DIR / str(collection_id)
        if folder_path.exists():
            shutil.rmtree(folder_path)


