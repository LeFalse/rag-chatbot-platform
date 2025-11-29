"""Conversation repository."""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Repository for Conversation model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Conversation, session)

    async def get_by_collection(
        self,
        collection_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Conversation]:
        """Get all conversations for a collection."""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.collection_id == collection_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_with_messages(
        self,
        conversation_id: UUID,
    ) -> Conversation | None:
        """Get conversation with its messages loaded."""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    async def get_recent(
        self,
        limit: int = 10,
    ) -> Sequence[Conversation]:
        """Get most recent conversations."""
        result = await self.session.execute(
            select(Conversation)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
