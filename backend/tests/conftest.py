"""Pytest fixtures for testing."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models.chunk import Chunk
from app.models.collection import Collection
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.message import Message
from app.models.metric import Metric

settings = get_settings()


@pytest_asyncio.fixture(scope="function")
async def engine():
    """Create engine for each test function to avoid event loop issues."""
    test_engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=2,
        max_overflow=5,
        pool_pre_ping=True,
    )
    yield test_engine
    await test_engine.dispose()


class TestSession(AsyncSession):
    """Session wrapper that converts commits to flushes for test isolation."""

    async def commit(self) -> None:
        """Convert commit to flush to prevent actual database commits."""
        await self.flush()


@pytest_asyncio.fixture(scope="function")
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a session that auto-rollbacks after each test.

    Uses a transaction that is never committed, ensuring test isolation.
    Commits are converted to flushes to prevent data persistence.
    """
    # Start a connection with a transaction
    async with engine.connect() as connection:
        # Begin a non-ORM transaction
        trans = await connection.begin()

        # Create test session that prevents commits
        async_session = TestSession(
            bind=connection,
            expire_on_commit=False,
        )

        try:
            yield async_session
        finally:
            # Always rollback - this discards all changes
            await async_session.close()
            await trans.rollback()


# Keep async_session as alias for backward compatibility
@pytest_asyncio.fixture(scope="function")
async def async_session(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Alias for session fixture for backward compatibility."""
    yield session


@pytest.fixture
def sample_collection_data() -> dict:
    """Sample collection data for testing."""
    return {
        "name": f"test-collection-{uuid4().hex[:8]}",
        "description": "Test collection for unit tests",
        "embedding_model": "nomic-embed-text",
        "embedding_dimension": 768,
    }


@pytest.fixture
def sample_document_data() -> dict:
    """Sample document data for testing."""
    return {
        "filename": f"test-doc-{uuid4().hex[:8]}.txt",
        "content_type": "text/plain",
        "file_size": 1024,
        "metadata_": {"source": "test"},
    }


@pytest.fixture
def sample_chunk_data() -> dict:
    """Sample chunk data for testing."""
    return {
        "content": "This is a test chunk content for unit testing.",
        "chunk_index": 0,
        "metadata_": {"page": 1},
    }


@pytest.fixture
def sample_conversation_data() -> dict:
    """Sample conversation data for testing."""
    return {
        "title": f"Test Conversation {uuid4().hex[:8]}",
    }


@pytest.fixture
def sample_message_data() -> dict:
    """Sample message data for testing."""
    return {
        "role": "user",
        "content": "What is the meaning of life?",
        "tokens_used": 10,
        "latency_ms": 100,
        "model": "test-model",
    }


@pytest_asyncio.fixture
async def collection(
    session: AsyncSession,
    sample_collection_data: dict,
) -> Collection:
    """Create a test collection (auto-rolled back after test)."""
    coll = Collection(**sample_collection_data)
    session.add(coll)
    await session.flush()
    return coll


@pytest_asyncio.fixture
async def document(
    session: AsyncSession,
    collection: Collection,
    sample_document_data: dict,
) -> Document:
    """Create a test document (auto-rolled back after test)."""
    doc = Document(collection_id=collection.id, **sample_document_data)
    session.add(doc)
    await session.flush()
    return doc


@pytest_asyncio.fixture
async def conversation(
    session: AsyncSession,
    collection: Collection,
    sample_conversation_data: dict,
) -> Conversation:
    """Create a test conversation (auto-rolled back after test)."""
    conv = Conversation(
        collection_id=collection.id,
        **sample_conversation_data,
    )
    session.add(conv)
    await session.flush()
    return conv


@pytest.fixture
def client(session):
    """Create a test client with the test database session."""
    # Override get_session to return the test session
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
