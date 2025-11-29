"""Tests for DocumentService."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collection import Collection
from app.models.document import Document
from app.services.document_service import DocumentService


@pytest.fixture
def temp_upload_dir(tmp_path):
    """Create a temporary upload directory."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return upload_dir


@pytest.mark.asyncio
async def test_document_upload(session: AsyncSession, temp_upload_dir):
    """Test uploading a document."""
    # Create a test collection
    collection = Collection(
        name="Test Collection",
        embedding_model="test-model",
        embedding_dimension=1536,
    )
    session.add(collection)
    await session.flush()

    # Create service with mocked upload directory
    service = DocumentService(session)
    service.UPLOAD_DIR = temp_upload_dir

    # Upload a document
    file_content = b"Test document content"
    document = await service.upload_document(
        collection.id,
        file_content,
        "test.txt",
        "text/plain",
    )

    assert document.filename == "test.txt"
    assert document.collection_id == collection.id
    assert document.file_size == len(file_content)
    assert document.content_type == "text/plain"

    # Verify file was written
    file_path = temp_upload_dir / str(collection.id) / "test.txt"
    assert file_path.exists()
    assert file_path.read_bytes() == file_content


@pytest.mark.asyncio
async def test_document_upload_duplicate(session: AsyncSession, temp_upload_dir):
    """Test uploading a duplicate document raises error."""
    collection = Collection(
        name="Test Collection",
        embedding_model="test-model",
        embedding_dimension=1536,
    )
    session.add(collection)
    await session.flush()

    service = DocumentService(session)
    service.UPLOAD_DIR = temp_upload_dir

    # Upload first document
    await service.upload_document(
        collection.id,
        b"content",
        "test.txt",
        "text/plain",
    )

    # Try to upload duplicate
    with pytest.raises(ValueError, match="already exists"):
        await service.upload_document(
            collection.id,
            b"different content",
            "test.txt",
            "text/plain",
        )


@pytest.mark.asyncio
async def test_document_upload_invalid_collection(session: AsyncSession, temp_upload_dir):
    """Test uploading to non-existent collection."""
    from uuid import uuid4

    service = DocumentService(session)
    service.UPLOAD_DIR = temp_upload_dir

    with pytest.raises(ValueError, match="not found"):
        await service.upload_document(
            uuid4(),
            b"content",
            "test.txt",
            "text/plain",
        )


@pytest.mark.asyncio
async def test_document_upload_file_too_large(session: AsyncSession, temp_upload_dir):
    """Test uploading a file that's too large."""
    collection = Collection(
        name="Test Collection",
        embedding_model="test-model",
        embedding_dimension=1536,
    )
    session.add(collection)
    await session.flush()

    service = DocumentService(session)
    service.UPLOAD_DIR = temp_upload_dir
    service.MAX_FILE_SIZE = 100  # Set low limit for testing

    with pytest.raises(ValueError, match="exceeds maximum"):
        await service.upload_document(
            collection.id,
            b"x" * 101,
            "large.txt",
            "text/plain",
        )


@pytest.mark.asyncio
async def test_document_process_and_chunk(session: AsyncSession, temp_upload_dir):
    """Test processing and chunking a document."""
    from app.models.chunk import Chunk

    collection = Collection(
        name="Test Collection",
        embedding_model="test-model",
        embedding_dimension=1536,
    )
    session.add(collection)
    await session.flush()

    # Create a document file
    service = DocumentService(session)
    service.UPLOAD_DIR = temp_upload_dir

    document_text = "This is the first sentence. This is the second sentence. " * 20
    document = await service.upload_document(
        collection.id,
        document_text.encode(),
        "test.txt",
        "text/plain",
    )

    # Process and chunk
    chunks = await service.process_and_chunk(
        document.id,
        chunk_size=100,
        overlap=10,
    )

    assert len(chunks) > 0
    assert all(isinstance(chunk, Chunk) for chunk in chunks)
    assert all(chunk.document_id == document.id for chunk in chunks)
    assert chunks[0].chunk_index == 0
    assert chunks[-1].chunk_index == len(chunks) - 1


@pytest.mark.asyncio
async def test_document_delete(session: AsyncSession, temp_upload_dir):
    """Test deleting a document."""
    collection = Collection(
        name="Test Collection",
        embedding_model="test-model",
        embedding_dimension=1536,
    )
    session.add(collection)
    await session.flush()

    service = DocumentService(session)
    service.UPLOAD_DIR = temp_upload_dir

    document = await service.upload_document(
        collection.id,
        b"content",
        "test.txt",
        "text/plain",
    )

    # Verify file exists
    file_path = temp_upload_dir / str(collection.id) / "test.txt"
    assert file_path.exists()

    # Delete document
    await service.delete_document(document.id)

    # Verify file is deleted
    assert not file_path.exists()

    # Verify document is deleted from DB
    deleted_doc = await session.get(Document, document.id)
    assert deleted_doc is None


@pytest.mark.asyncio
async def test_document_stats(session: AsyncSession, temp_upload_dir):
    """Test getting document statistics."""
    collection = Collection(
        name="Test Collection",
        embedding_model="test-model",
        embedding_dimension=1536,
    )
    session.add(collection)
    await session.flush()

    service = DocumentService(session)
    service.UPLOAD_DIR = temp_upload_dir

    document_text = "This is a test. " * 10
    document = await service.upload_document(
        collection.id,
        document_text.encode(),
        "test.txt",
        "text/plain",
    )

    # Process and chunk
    await service.process_and_chunk(document.id, chunk_size=50, overlap=5)

    # Get stats
    stats = await service.get_document_stats(document.id)

    assert stats["document_id"] == str(document.id)
    assert stats["filename"] == "test.txt"
    assert stats["chunk_count"] > 0
    assert stats["total_content_chars"] > 0
    assert stats["avg_chunk_size"] > 0
