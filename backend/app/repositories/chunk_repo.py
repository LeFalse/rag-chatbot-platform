"""Chunk repository with vector search capabilities."""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.repositories.base import BaseRepository


class ChunkRepository(BaseRepository[Chunk]):
    """Repository for Chunk model with vector search."""

    def __init__(self, session: AsyncSession):
        super().__init__(Chunk, session)

    async def get_by_document(
        self,
        document_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Chunk]:
        """Get all chunks for a document."""
        result = await self.session.execute(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def search_similar(
        self,
        embedding: list[float],
        collection_id: UUID,
        limit: int = 5,
        threshold: float = 0.7,
    ) -> Sequence[tuple[Chunk, float]]:
        """Search for similar chunks using vector similarity.

        Uses cosine distance (lower is better, 0 = identical).
        Returns chunks with similarity score (1 - distance).
        """
        # pgvector cosine distance operator: <=>
        # We join through documents to filter by collection
        query = text(
            """
            SELECT c.*, 1 - (c.embedding <=> :embedding) as similarity
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE d.collection_id = :collection_id
            AND c.embedding IS NOT NULL
            AND 1 - (c.embedding <=> :embedding) >= :threshold
            ORDER BY c.embedding <=> :embedding
            LIMIT :limit
            """
        )

        result = await self.session.execute(
            query,
            {
                "embedding": str(embedding),
                "collection_id": str(collection_id),
                "threshold": threshold,
                "limit": limit,
            },
        )

        rows = result.fetchall()
        chunks_with_scores = []

        for row in rows:
            chunk = Chunk(
                id=row.id,
                document_id=row.document_id,
                content=row.content,
                chunk_index=row.chunk_index,
                metadata_=row.metadata,
                created_at=row.created_at,
            )
            chunks_with_scores.append((chunk, row.similarity))

        return chunks_with_scores

    async def bulk_create(self, chunks: list[Chunk]) -> list[Chunk]:
        """Create multiple chunks at once."""
        self.session.add_all(chunks)
        await self.session.flush()
        for chunk in chunks:
            await self.session.refresh(chunk)
        return chunks

    async def delete_by_document(self, document_id: UUID) -> int:
        """Delete all chunks for a document."""
        result = await self.session.execute(
            text("DELETE FROM chunks WHERE document_id = :document_id"),
            {"document_id": str(document_id)},
        )
        return result.rowcount
