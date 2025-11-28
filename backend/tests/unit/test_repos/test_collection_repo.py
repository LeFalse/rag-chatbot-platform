"""Tests for CollectionRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Collection
from app.repositories import CollectionRepository


@pytest.mark.asyncio
async def test_create_collection(
    async_session: AsyncSession,
    sample_collection_data: dict,
):
    """Test creating a collection."""
    repo = CollectionRepository(async_session)
    collection = Collection(**sample_collection_data)

    result = await repo.create(collection)

    assert result.id is not None
    assert result.name == sample_collection_data["name"]
    assert result.embedding_model == sample_collection_data["embedding_model"]

    # Cleanup
    await repo.delete(result.id)


@pytest.mark.asyncio
async def test_get_collection_by_id(
    async_session: AsyncSession,
    collection: Collection,
):
    """Test getting a collection by ID."""
    repo = CollectionRepository(async_session)

    result = await repo.get_by_id(collection.id)

    assert result is not None
    assert result.id == collection.id
    assert result.name == collection.name


@pytest.mark.asyncio
async def test_get_collection_by_name(
    async_session: AsyncSession,
    collection: Collection,
):
    """Test getting a collection by name."""
    repo = CollectionRepository(async_session)

    result = await repo.get_by_name(collection.name)

    assert result is not None
    assert result.name == collection.name


@pytest.mark.asyncio
async def test_get_nonexistent_collection(
    async_session: AsyncSession,
):
    """Test getting a nonexistent collection returns None."""
    repo = CollectionRepository(async_session)
    from uuid import uuid4

    result = await repo.get_by_id(uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_search_collections_by_name(
    async_session: AsyncSession,
    collection: Collection,
):
    """Test searching collections by name."""
    repo = CollectionRepository(async_session)

    # Search with partial name
    results = await repo.search_by_name("test")

    assert len(results) >= 1
    assert any(c.id == collection.id for c in results)


@pytest.mark.asyncio
async def test_count_collections(
    async_session: AsyncSession,
    collection: Collection,
):
    """Test counting collections."""
    repo = CollectionRepository(async_session)

    count = await repo.count()

    assert count >= 1
