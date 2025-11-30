"""Document repository."""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Document, session)

    async def get_by_collection(
        self,
        collection_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Document]:
        """Get all documents in a collection."""
        result = await self.session.execute(
            select(Document)
            .where(Document.collection_id == collection_id)
            .offset(skip)
            .limit(limit)
            .order_by(Document.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_collection_with_chunks(
        self,
        collection_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Document]:
        """Get all documents in a collection with chunks loaded."""
        result = await self.session.execute(
            select(Document)
            .where(Document.collection_id == collection_id)
            .options(selectinload(Document.chunks))
            .offset(skip)
            .limit(limit)
            .order_by(Document.created_at.desc())
        )
        return result.scalars().all()

    async def get_with_chunks(self, document_id: UUID) -> Document | None:
        """Get document with its chunks loaded."""
        result = await self.session.execute(
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.chunks))
        )
        return result.scalar_one_or_none()

    async def get_by_filename(
        self,
        collection_id: UUID,
        filename: str,
    ) -> Document | None:
        """Get document by filename in a collection."""
        result = await self.session.execute(
            select(Document).where(
                Document.collection_id == collection_id,
                Document.filename == filename,
            )
        )
        return result.scalar_one_or_none()
