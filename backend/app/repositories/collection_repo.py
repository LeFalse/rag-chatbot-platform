"""Collection repository."""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Collection
from app.repositories.base import BaseRepository


class CollectionRepository(BaseRepository[Collection]):
    """Repository for Collection model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Collection, session)

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
