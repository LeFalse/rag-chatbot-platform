"""Tests for ChatService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.collection import Collection
from app.models.conversation import Conversation
from app.models.document import Document
from app.providers.llm.types import ChatMessage, StreamChunk
from app.services.cache.session_cache import SessionCache
from app.services.chat_service import ChatService
from app.services.embedding_service import EmbeddingService


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = AsyncMock()
    provider.provider_name = "test-llm"
    provider.generate_stream = AsyncMock()
    return provider


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = AsyncMock(spec=EmbeddingService)
    service.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])
    return service


@pytest.fixture
def mock_embedding_provider():
    """Create a mock embedding provider."""
    provider = AsyncMock()
    provider.provider_name = "test-embedding"
    return provider


@pytest.fixture
def mock_session_cache():
    """Create a mock session cache."""
    cache = AsyncMock(spec=SessionCache)
    cache.get_messages = AsyncMock(return_value=[])
    cache.add_message = AsyncMock()
    return cache


@pytest.mark.asyncio
async def test_answer_question_streaming(
    session: AsyncSession,
    mock_llm_provider,
    mock_embedding_provider,
    mock_embedding_service,
    mock_session_cache,
):
    """Test answering a question with streaming."""
    # Create test data
    collection = Collection(
        name="Test Collection",
        embedding_model="test-model",
        embedding_dimension=3,
    )
    session.add(collection)
    await session.flush()

    conversation = Conversation(
        collection_id=collection.id,
        title="Test Conversation",
    )
    session.add(conversation)
    await session.flush()

    document = Document(
        collection_id=collection.id,
        filename="test.txt",
        content_type="text/plain",
        file_size=100,
    )
    session.add(document)
    await session.flush()

    chunk = Chunk(
        document_id=document.id,
        content="This is test content.",
        chunk_index=0,
    )
    session.add(chunk)
    await session.flush()

    # Mock embedding service to return valid embedding
    mock_embedding_service.embed_text.return_value = [0.1, 0.2, 0.3]

    # Create service
    service = ChatService(
        session,
        mock_llm_provider,
        mock_embedding_provider,
        mock_embedding_service,
        mock_session_cache,
    )

    # Mock streaming response - create proper async generator
    async def mock_generate_stream(*args, **kwargs):
        yield StreamChunk(content="Hello ", finish_reason=None)
        yield StreamChunk(content="world!", finish_reason="stop")

    # Track calls to the generator
    call_tracker = MagicMock()
    original_generator = mock_generate_stream

    async def tracked_generator(*args, **kwargs):
        call_tracker(*args, **kwargs)
        async for item in original_generator(*args, **kwargs):
            yield item

    mock_llm_provider.generate_stream = tracked_generator

    # Mock chunk search (would be done by chunk_repo in real code)
    # We'll mock the search to return our test chunk
    with patch.object(
        service.chunk_repo,
        "search_similar",
        return_value=[(chunk, 0.95, "test.txt")],
    ):
        # Stream answer
        response_chunks = []
        async for chunk in service.answer_question(
            conversation.id,
            collection.id,
            "What is test content?",
        ):
            response_chunks.append(chunk)

    # Verify streaming worked (includes LLM response + sources marker)
    assert response_chunks[0] == "Hello "
    assert response_chunks[1] == "world!"
    # Last chunk should be the sources metadata marker
    assert "[SOURCES]" in response_chunks[-1]
    assert "test.txt" in response_chunks[-1]
    call_tracker.assert_called_once()

    # Verify context was built
    call_args = call_tracker.call_args
    messages = call_args[0][0]
    assert any(
        "context" in (m.content if hasattr(m, 'content') else m.get('content', '')).lower()
        for m in messages
    )


@pytest.mark.asyncio
async def test_answer_question_with_cached_messages(
    session: AsyncSession,
    mock_llm_provider,
    mock_embedding_provider,
    mock_embedding_service,
    mock_session_cache,
):
    """Test answering question with conversation history from cache."""
    collection = Collection(
        name="Test Collection",
        embedding_model="test-model",
        embedding_dimension=3,
    )
    session.add(collection)
    await session.flush()

    conversation = Conversation(
        collection_id=collection.id,
        title="Test Conversation",
    )
    session.add(conversation)
    await session.flush()

    # Create service with cached messages (MessageData format)
    from app.services.cache.types import MessageData
    cached_messages: list[MessageData] = [
        {"role": "user", "content": "Previous question", "timestamp": "2024-01-01T00:00:00"},
        {"role": "assistant", "content": "Previous answer", "timestamp": "2024-01-01T00:00:01"},
    ]
    mock_session_cache.get_messages.return_value = cached_messages

    service = ChatService(
        session,
        mock_llm_provider,
        mock_embedding_provider,
        mock_embedding_service,
        mock_session_cache,
    )

    # Mock conversation repository to return conversation
    service.conv_repo = AsyncMock()
    service.conv_repo.get_with_messages = AsyncMock(return_value=conversation)

    # Mock streaming
    async def mock_generate_stream(*args, **kwargs):
        yield StreamChunk(content="Response", finish_reason="stop")

    # Track calls to the generator
    call_tracker = MagicMock()
    original_generator = mock_generate_stream

    async def tracked_generator(*args, **kwargs):
        call_tracker(*args, **kwargs)
        async for item in original_generator(*args, **kwargs):
            yield item

    mock_llm_provider.generate_stream = tracked_generator

    # Mock chunk search
    with patch.object(
        service.chunk_repo,
        "search_similar",
        return_value=[],
    ):
        response_chunks = []
        async for chunk in service.answer_question(
            conversation.id,
            collection.id,
            "New question",
        ):
            response_chunks.append(chunk)

    # Verify cached messages were used
    call_args = call_tracker.call_args
    messages = call_args[0][0]
    # Should have cached messages + system + new question
    assert len(messages) >= 3


@pytest.mark.asyncio
async def test_get_conversation_history(
    session: AsyncSession,
    mock_llm_provider,
    mock_embedding_provider,
    mock_embedding_service,
    mock_session_cache,
):
    """Test retrieving conversation history."""
    collection = Collection(
        name="Test Collection",
        embedding_model="test-model",
        embedding_dimension=3,
    )
    session.add(collection)
    await session.flush()

    conversation = Conversation(
        collection_id=collection.id,
        title="Test Conversation",
    )
    session.add(conversation)
    await session.flush()

    # Create service
    service = ChatService(
        session,
        mock_llm_provider,
        mock_embedding_provider,
        mock_embedding_service,
        mock_session_cache,
    )

    # Mock conversation repository
    service.conv_repo = AsyncMock()
    service.conv_repo.get_with_messages = AsyncMock(return_value=conversation)
    service.msg_repo = AsyncMock()
    service.msg_repo.get_by_conversation = AsyncMock(return_value=[])

    # Get history (will be empty in test)
    history = await service.get_conversation_history(conversation.id)

    assert isinstance(history, list)
    assert all("role" in msg and "content" in msg for msg in history)


@pytest.mark.asyncio
async def test_build_context_with_chunks(
    session: AsyncSession,
    mock_llm_provider,
    mock_embedding_provider,
    mock_embedding_service,
    mock_session_cache,
):
    """Test building context from chunks."""
    collection = Collection(
        name="Test Collection",
        embedding_model="test-model",
        embedding_dimension=3,
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

    chunk1 = Chunk(
        document_id=document.id,
        content="First chunk content",
        chunk_index=0,
    )
    chunk2 = Chunk(
        document_id=document.id,
        content="Second chunk content",
        chunk_index=1,
    )
    session.add_all([chunk1, chunk2])
    await session.flush()

    service = ChatService(
        session,
        mock_llm_provider,
        mock_embedding_provider,
        mock_embedding_service,
        mock_session_cache,
    )

    # Build context - now includes filename as third element
    similar_chunks = [(chunk1, 0.95, "test.txt"), (chunk2, 0.85, "test.txt")]
    context = service._build_context(similar_chunks)

    assert "First chunk content" in context
    assert "Second chunk content" in context
    assert "relevance" in context
    assert "test.txt" in context


@pytest.mark.asyncio
async def test_build_context_empty(
    session: AsyncSession,
    mock_llm_provider,
    mock_embedding_provider,
    mock_embedding_service,
    mock_session_cache,
):
    """Test building context with no chunks."""
    service = ChatService(
        session,
        mock_llm_provider,
        mock_embedding_provider,
        mock_embedding_service,
        mock_session_cache,
    )

    context = service._build_context([])

    assert "No relevant context" in context
