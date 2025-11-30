"""Tests for EmbeddingService."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.collection import Collection
from app.models.document import Document
from app.providers.embedding.types import EmbeddingResult, BatchEmbeddingResult
from app.services.cache.embedding_cache import EmbeddingCache
from app.services.cache.types import CachedEmbedding
from app.services.embedding_service import EmbeddingService


@pytest.fixture
def mock_embedding_provider():
    """Create a mock embedding provider."""
    provider = AsyncMock()
    provider.provider_name = "test-provider"
    provider.embed = AsyncMock()
    provider.embed_batch = AsyncMock()
    return provider


@pytest.fixture
def mock_embedding_cache():
    """Create a mock embedding cache."""
    cache = AsyncMock(spec=EmbeddingCache)
    cache.get_embedding = AsyncMock(return_value=None)
    cache.set_embedding = AsyncMock(return_value=True)
    # get_batch returns (cached_embeddings, misses)
    cache.get_batch = AsyncMock(return_value=([None, None], [0, 1]))
    cache.get_stats = AsyncMock(return_value={"hits": 0, "misses": 1})
    return cache


@pytest.mark.asyncio
async def test_embed_text_cache_miss(
    session: AsyncSession, mock_embedding_provider, mock_embedding_cache
):
    """Test embedding text with cache miss."""
    service = EmbeddingService(session, mock_embedding_provider, mock_embedding_cache)

    # Mock provider response
    test_embedding = [0.1, 0.2, 0.3]
    mock_embedding_provider.embed.return_value = EmbeddingResult(
        embedding=test_embedding,
        model="test-model",
        tokens_used=10,
    )

    # Call embed_text
    result = await service.embed_text("test text")

    assert result == test_embedding
    mock_embedding_provider.embed.assert_called_once()
    mock_embedding_cache.set_embedding.assert_called_once()


@pytest.mark.asyncio
async def test_embed_text_cache_hit(
    session: AsyncSession, mock_embedding_provider, mock_embedding_cache
):
    """Test embedding text with cache hit."""
    service = EmbeddingService(session, mock_embedding_provider, mock_embedding_cache)

    # Mock cache hit with CachedEmbedding object
    cached_embedding = [0.4, 0.5, 0.6]
    mock_cached = MagicMock(spec=CachedEmbedding)
    mock_cached.embedding = cached_embedding
    mock_embedding_cache.get_embedding.return_value = mock_cached

    # Call embed_text
    result = await service.embed_text("test text")

    assert result == cached_embedding
    mock_embedding_provider.embed.assert_not_called()
    mock_embedding_cache.set_embedding.assert_not_called()


@pytest.mark.asyncio
async def test_embed_texts_batch(
    session: AsyncSession, mock_embedding_provider, mock_embedding_cache
):
    """Test batch embedding texts."""
    service = EmbeddingService(session, mock_embedding_provider, mock_embedding_cache)

    # Mock batch provider response
    embeddings = [[0.1, 0.2], [0.3, 0.4]]
    mock_embedding_provider.embed_batch.return_value = BatchEmbeddingResult(
        embeddings=embeddings,
        model="test-model",
        total_tokens=20,
    )
    # get_batch returns (cached_embeddings, misses)
    mock_embedding_cache.get_batch.return_value = ([None, None], [0, 1])

    # Call embed_texts_batch
    result = await service.embed_texts_batch(["text1", "text2"])

    assert result == embeddings
    mock_embedding_provider.embed_batch.assert_called_once()
    assert mock_embedding_cache.set_embedding.call_count == 2


@pytest.mark.asyncio
async def test_embed_chunks(
    session: AsyncSession, mock_embedding_provider, mock_embedding_cache
):
    """Test embedding chunks from a document."""
    # Create collection and document
    collection = Collection(
        name="Test Collection",
        embedding_model="test-model",
        embedding_dimension=768,  # Match Chunk model's Vector dimension
    )
    session.add(collection)
    await session.flush()

    document = Document(
        collection_id=collection.id,
        filename="test.txt",
        content_type="text/plain",
        file_size=100,
    )
    session.add(document)
    await session.flush()

    # Create chunks
    chunks = [
        Chunk(
            document_id=document.id,
            content="chunk 1",
            chunk_index=0,
        ),
        Chunk(
            document_id=document.id,
            content="chunk 2",
            chunk_index=1,
        ),
    ]
    session.add_all(chunks)
    await session.flush()

    # Mock provider response - embeddings must have 768 dimensions
    test_embedding = [0.1] * 768
    embeddings = [test_embedding, test_embedding]
    mock_embedding_provider.embed_batch.return_value = BatchEmbeddingResult(
        embeddings=embeddings,
        model="test-model",
        total_tokens=20,
    )
    # get_batch returns (cached_embeddings, misses)
    mock_embedding_cache.get_batch.return_value = ([None, None], [0, 1])

    # Create service and embed chunks
    service = EmbeddingService(session, mock_embedding_provider, mock_embedding_cache)
    count = await service.embed_chunks(document.id)

    assert count == 2
    mock_embedding_provider.embed_batch.assert_called_once()


@pytest.mark.asyncio
async def test_get_cache_stats(
    session: AsyncSession, mock_embedding_provider, mock_embedding_cache
):
    """Test getting cache statistics."""
    service = EmbeddingService(session, mock_embedding_provider, mock_embedding_cache)

    stats = await service.get_cache_stats()

    assert stats == {"hits": 0, "misses": 1}
    mock_embedding_cache.get_stats.assert_called_once()
