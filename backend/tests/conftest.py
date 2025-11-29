"""Pytest fixtures for testing."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import Base
from app.models.chunk import Chunk
from app.models.collection import Collection
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.message import Message
from app.models.metric import Metric

settings = get_settings()


@pytest.fixture(autouse=True, scope="function")
def reset_db_isolation():
    """Reset DB isolation for each test."""
    yield


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create a single engine for all tests to avoid memory issues."""
    test_engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for testing, reusing the same engine."""
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=True,
    )

    test_session = await async_session_maker().__aenter__()
    try:
        yield test_session
    finally:
        # Ensure proper cleanup of the session
        try:
            await test_session.rollback()
        except Exception:
            pass
        try:
            await test_session.close()
        except Exception:
            pass
        # Dispose of the connection back to the pool
        await engine.dispose()


# Keep async_session as alias for backward compatibility
async_session = session


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
    async_session: AsyncSession,
    sample_collection_data: dict,
) -> AsyncGenerator[Collection, None]:
    """Create a test collection."""
    coll = Collection(**sample_collection_data)
    async_session.add(coll)
    await async_session.flush()
    yield coll
    await async_session.delete(coll)
    await async_session.flush()


@pytest_asyncio.fixture
async def document(
    async_session: AsyncSession,
    collection: Collection,
    sample_document_data: dict,
) -> AsyncGenerator[Document, None]:
    """Create a test document."""
    doc = Document(collection_id=collection.id, **sample_document_data)
    async_session.add(doc)
    await async_session.flush()
    yield doc
    await async_session.delete(doc)
    await async_session.flush()


@pytest_asyncio.fixture
async def conversation(
    async_session: AsyncSession,
    collection: Collection,
    sample_conversation_data: dict,
) -> AsyncGenerator[Conversation, None]:
    """Create a test conversation."""
    conv = Conversation(
        collection_id=collection.id,
        **sample_conversation_data,
    )
    async_session.add(conv)
    await async_session.flush()
    yield conv
    await async_session.delete(conv)
    await async_session.flush()
