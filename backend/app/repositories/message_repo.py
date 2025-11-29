"""Message repository."""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Repository for Message model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)

    async def get_by_conversation(
        self,
        conversation_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Message]:
        """Get all messages for a conversation."""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_recent_messages(
        self,
        conversation_id: UUID,
        limit: int = 50,
    ) -> Sequence[Message]:
        """Get most recent messages for context window."""
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        # Reverse to get chronological order
        messages = list(result.scalars().all())
        messages.reverse()
        return messages

    async def count_by_conversation(self, conversation_id: UUID) -> int:
        """Count messages in a conversation."""
        result = await self.session.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.conversation_id == conversation_id)
        )
        return result.scalar_one()
