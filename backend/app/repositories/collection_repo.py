"""Collection repository."""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collection import Collection
from app.repositories.base import BaseRepository


class CollectionRepository(BaseRepository[Collection]):
    """Repository for Collection model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Collection, session)

    async def get_all_with_documents(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Collection]:
        """Get all collections with eagerly loaded documents."""
        result = await self.session.execute(
            select(Collection)
            .options(selectinload(Collection.documents))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_name(self, name: str) -> Collection | None:
        """Get collection by name."""
        result = await self.session.execute(
            select(Collection).where(Collection.name == name)
        )
        return result.scalar_one_or_none()

    async def search_by_name(
        self,
        query: str,
        limit: int = 10,
    ) -> Sequence[Collection]:
        """Search collections by name (case insensitive)."""
        result = await self.session.execute(
            select(Collection)
            .where(Collection.name.ilike(f"%{query}%"))
            .limit(limit)
        )
        return result.scalars().all()
