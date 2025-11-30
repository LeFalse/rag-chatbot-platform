"""Embedding service - generates embeddings with caching."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.embedding.base import BaseEmbeddingProvider
from app.repositories.chunk_repo import ChunkRepository
from app.services.cache.embedding_cache import EmbeddingCache


class EmbeddingService:
    """Service for generating embeddings with Redis cache."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: BaseEmbeddingProvider,
        cache: EmbeddingCache,
    ):
        """Initialize service with provider and cache.

        Args:
            session: SQLAlchemy async session.
            embedding_provider: Provider for embedding generation.
            cache: Cache for storing embeddings.
        """
        self.session = session
        self.provider = embedding_provider
        self.cache = cache
        self.chunk_repo = ChunkRepository(session)

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for text with caching.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector.

        Raises:
            ValueError: If embedding generation fails.
        """
        # Check cache first
        cached = await self.cache.get_embedding(text, self.provider.provider_name)
        if cached:
            return cached.embedding

        # Generate embedding
        result = await self.provider.embed(text)
        embedding = result.embedding

        # Store in cache
        await self.cache.set_embedding(text, embedding, self.provider.provider_name)

        return embedding

    async def embed_texts_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts with caching.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors.

        Raises:
            ValueError: If embedding generation fails.
        """
        embeddings: list[list[float]] = []
        texts_to_embed: list[int] = []
        model = self.provider.provider_name

        # Check cache for all texts
        cached_embeddings, misses = await self.cache.get_batch(texts, model)

        for i, cached in enumerate(cached_embeddings):
            if cached:
                embeddings.append(cached.embedding)
            else:
                embeddings.append([])  # Placeholder
                texts_to_embed.append(i)

        # Generate missing embeddings
        if texts_to_embed:
            texts_to_generate = [texts[i] for i in texts_to_embed]
            result = await self.provider.embed_batch(texts_to_generate)

            # Store in cache and replace placeholders
            for i, idx in enumerate(texts_to_embed):
                embedding = result.embeddings[i]
                embeddings[idx] = embedding
                await self.cache.set_embedding(texts[idx], embedding, model)

        return embeddings

    async def embed_chunks(self, document_id: UUID) -> int:
        """Generate and store embeddings for all chunks in a document.

        Args:
            document_id: Document whose chunks to embed.

        Returns:
            Number of chunks embedded.

        Raises:
            ValueError: If document not found or embedding fails.
        """
        # Get all chunks for document
        chunks = await self.chunk_repo.get_by_document(
            document_id,
            skip=0,
            limit=1000,
        )

        if not chunks:
            return 0

        # Extract chunk contents
        chunk_contents = [chunk.content for chunk in chunks]

        # Generate embeddings
        embeddings = await self.embed_texts_batch(chunk_contents)

        # Update chunks with embeddings
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding

        # Commit changes
        await self.session.flush()

        return len(chunks)

    async def get_cache_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache hit rate and other stats.
        """
        return await self.cache.get_stats()
