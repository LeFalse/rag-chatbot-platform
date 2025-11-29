"""Tests for ConversationRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collection import Collection
from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.message_repo import MessageRepository


@pytest.mark.asyncio
async def test_create_conversation(
    async_session: AsyncSession,
    collection: Collection,
    sample_conversation_data: dict,
):
    """Test creating a conversation."""
    repo = ConversationRepository(async_session)
    conversation = Conversation(
        collection_id=collection.id,
        **sample_conversation_data,
    )

    result = await repo.create(conversation)

    assert result.id is not None
    assert result.title == sample_conversation_data["title"]
    assert result.collection_id == collection.id

    # Cleanup
    await repo.delete(result.id)


@pytest.mark.asyncio
async def test_get_conversations_by_collection(
    async_session: AsyncSession,
    conversation: Conversation,
):
    """Test getting conversations by collection."""
    repo = ConversationRepository(async_session)

    results = await repo.get_by_collection(conversation.collection_id)

    assert len(results) >= 1
    assert any(c.id == conversation.id for c in results)


@pytest.mark.asyncio
async def test_get_recent_conversations(
    async_session: AsyncSession,
    conversation: Conversation,
):
    """Test getting recent conversations."""
    repo = ConversationRepository(async_session)

    results = await repo.get_recent(limit=10)

    assert len(results) >= 1


@pytest.mark.asyncio
async def test_get_conversation_with_messages(
    async_session: AsyncSession,
    conversation: Conversation,
    sample_message_data: dict,
):
    """Test getting conversation with messages."""
    conv_repo = ConversationRepository(async_session)
    msg_repo = MessageRepository(async_session)

    # Add a message
    message = Message(
        conversation_id=conversation.id,
        **sample_message_data,
    )
    await msg_repo.create(message)

    # Get conversation with messages
    result = await conv_repo.get_with_messages(conversation.id)

    assert result is not None
    assert len(result.messages) >= 1

    # Cleanup
    await msg_repo.delete(message.id)
