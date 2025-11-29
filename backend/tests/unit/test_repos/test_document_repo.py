"""Tests for DocumentRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collection import Collection
from app.models.document import Document
from app.repositories.document_repo import DocumentRepository


@pytest.mark.asyncio
async def test_create_document(
    async_session: AsyncSession,
    collection: Collection,
    sample_document_data: dict,
):
    """Test creating a document."""
    repo = DocumentRepository(async_session)
    document = Document(collection_id=collection.id, **sample_document_data)

    result = await repo.create(document)

    assert result.id is not None
    assert result.filename == sample_document_data["filename"]
    assert result.collection_id == collection.id

    # Cleanup
    await repo.delete(result.id)


@pytest.mark.asyncio
async def test_get_documents_by_collection(
    async_session: AsyncSession,
    document: Document,
):
    """Test getting documents by collection."""
    repo = DocumentRepository(async_session)

    results = await repo.get_by_collection(document.collection_id)

    assert len(results) >= 1
    assert any(d.id == document.id for d in results)


@pytest.mark.asyncio
async def test_get_document_by_filename(
    async_session: AsyncSession,
    document: Document,
):
    """Test getting document by filename."""
    repo = DocumentRepository(async_session)

    result = await repo.get_by_filename(
        document.collection_id,
        document.filename,
    )

    assert result is not None
    assert result.id == document.id


@pytest.mark.asyncio
async def test_delete_document(
    async_session: AsyncSession,
    collection: Collection,
    sample_document_data: dict,
):
    """Test deleting a document."""
    repo = DocumentRepository(async_session)
    document = Document(collection_id=collection.id, **sample_document_data)
    created = await repo.create(document)

    deleted = await repo.delete(created.id)

    assert deleted is True

    # Verify it's gone
    result = await repo.get_by_id(created.id)
    assert result is None
