"""Chat service - implements RAG pipeline with streaming."""

import time
from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.providers.embedding.base import BaseEmbeddingProvider
from app.providers.llm.base import BaseLLMProvider
from app.providers.llm.types import ChatMessage
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.message_repo import MessageRepository
from app.services.cache.session_cache import SessionCache
from app.services.embedding_service import EmbeddingService


class ChatService:
    """Service for chat with RAG (Retrieval-Augmented Generation)."""

    SYSTEM_PROMPT = """You are a helpful assistant answering questions based on provided documents.
Use the context provided to answer questions accurately.
If the answer is not in the context, say so clearly.
Always cite the source when referencing the documents."""

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: BaseLLMProvider,
        embedding_provider: BaseEmbeddingProvider,
        embedding_service: EmbeddingService,
        session_cache: SessionCache,
    ):
        """Initialize service with providers and cache.

        Args:
            session: SQLAlchemy async session.
            llm_provider: LLM provider for generation.
            embedding_provider: Embedding provider for queries.
            embedding_service: Service for generating embeddings.
            session_cache: Cache for conversation context.
        """
        self.session = session
        self.llm_provider = llm_provider
        self.embedding_provider = embedding_provider
        self.embedding_service = embedding_service
        self.session_cache = session_cache
        self.conv_repo = ConversationRepository(session)
        self.msg_repo = MessageRepository(session)
        self.chunk_repo = ChunkRepository(session)

    async def answer_question(
        self,
        conversation_id: UUID,
        collection_id: UUID,
        question: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
    ) -> AsyncIterator[str]:
        """Answer a question using RAG with streaming response.

        Args:
            conversation_id: Conversation to add message to.
            collection_id: Collection to search for context.
            question: User's question.
            top_k: Number of chunks to retrieve.
            similarity_threshold: Minimum similarity score.

        Yields:
            Streaming response chunks.

        Raises:
            ValueError: If conversation or collection not found.
        """
        # Get conversation (verify it exists)
        conversation = await self.conv_repo.get_with_messages(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Get recent conversation history from cache
        cache_key = f"conv:{conversation_id}:messages"
        cached_messages = await self.session_cache.get_messages(cache_key)
        messages: list[ChatMessage] = cached_messages or []

        # Generate embedding for question
        question_embedding = await self.embedding_service.embed_text(question)

        # Search for similar chunks
        start_time = time.time()
        similar_chunks = await self.chunk_repo.search_similar(
            question_embedding,
            collection_id,
            limit=top_k,
            threshold=similarity_threshold,
        )
        search_latency_ms = int((time.time() - start_time) * 1000)

        # Build context from chunks
        context = self._build_context(similar_chunks)

        # Add user message to history
        user_message = ChatMessage(role="user", content=question)
        messages.append(user_message)

        # Save user message to DB
        user_db_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=question,
        )
        self.session.add(user_db_message)
        await self.session.flush()

        # Add system message with context if not already there
        has_system = any(
            getattr(m, "role", None) == "system" or
            (isinstance(m, dict) and m.get("role") == "system")
            for m in messages
        )

        if not has_system:
            system_message = ChatMessage(
                role="system",
                content=f"{self.SYSTEM_PROMPT}\n\nContext:\n{context}",
            )
            messages.insert(0, system_message)
        else:
            # Update system message with new context
            messages[0] = ChatMessage(
                role="system",
                content=f"{self.SYSTEM_PROMPT}\n\nContext:\n{context}",
            )

        # Generate streaming response
        response_content = ""
        start_time = time.time()

        async for chunk in self.llm_provider.generate_stream(messages):
            response_content += chunk.content
            yield chunk.content

        latency_ms = int((time.time() - start_time) * 1000)

        # Save assistant message to DB
        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=response_content,
            latency_ms=latency_ms,
            model=self.llm_provider.provider_name,
        )
        self.session.add(assistant_message)
        await self.session.flush()

        # Update session cache with new messages
        messages.append(ChatMessage(role="assistant", content=response_content))
        await self.session_cache.set_messages(cache_key, messages)

    async def get_conversation_history(
        self,
        conversation_id: UUID,
        limit: int = 50,
    ) -> list[dict]:
        """Get conversation history.

        Args:
            conversation_id: Conversation to get history for.
            limit: Maximum number of messages to return.

        Returns:
            List of messages.

        Raises:
            ValueError: If conversation not found.
        """
        conversation = await self.conv_repo.get_with_messages(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        messages = await self.msg_repo.get_by_conversation(
            conversation_id,
            limit=limit,
        )

        return [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ]

    def _build_context(
        self,
        similar_chunks: list[tuple],
    ) -> str:
        """Build context string from similar chunks.

        Args:
            similar_chunks: List of (chunk, similarity_score) tuples.

        Returns:
            Formatted context string.
        """
        if not similar_chunks:
            return "No relevant context found."

        context_parts = []
        for chunk, score in similar_chunks:
            context_parts.append(
                f"[Document: {chunk.document.filename} (relevance: {score:.2%})]\n"
                f"{chunk.content}\n"
            )

        return "\n".join(context_parts)
