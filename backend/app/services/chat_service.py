"""Chat service - implements RAG pipeline with streaming."""

import json
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
from app.services.language_utils import (
    LANGUAGE_INSTRUCTION,
    PERSONALITY_PROMPTS,
    detect_language_prefix,
    has_language_instruction,
)


class ChatService:
    """Service for chat with RAG (Retrieval-Augmented Generation)."""

    DEFAULT_SYSTEM_PROMPT = """You are a precise assistant that answers questions based ONLY on the provided documents.

Critical Instructions:
- Read the context CAREFULLY before answering
- Pay special attention to tables - read ALL columns and rows precisely
- Answer EXACTLY what is asked - do not generalize or summarize incorrectly
- "Manual" and "Manual with approval" are DIFFERENT things
- If the answer is not in the context, say "I couldn't find this information in the available documents"
- Do NOT mention document names, filenames, or sources in your response - sources are shown separately
- Do NOT mention relevance percentages, similarity scores, or technical metadata
- Do NOT invent information not present in the context
- Be direct and concise - just answer the question"""

    def _get_system_prompt(
        self,
        system_prompt: str | None = None,
        personality: str | None = None,
    ) -> tuple[str, str | None]:
        """Get the system prompt based on configuration.

        The final prompt is built by combining:
        1. Personality intro (if provided)
        2. Default RAG instructions (always included)

        Custom system prompt is returned separately to be placed AFTER
        the context for maximum priority.

        Args:
            system_prompt: Custom instructions to add after context.
            personality: Personality preset name.

        Returns:
            Tuple of (base_prompt, custom_instructions).
        """
        parts = []

        # Add personality intro if provided
        if personality and personality in PERSONALITY_PROMPTS:
            parts.append(PERSONALITY_PROMPTS[personality])

        # Default RAG instructions
        parts.append(self.DEFAULT_SYSTEM_PROMPT)

        return "\n\n".join(parts), system_prompt

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
        system_prompt: str | None = None,
        personality: str | None = None,
        temperature: float = 0.5,
        max_tokens: int = 512,
        collection_name: str | None = None,
    ) -> AsyncIterator[str]:
        """Answer a question using RAG with streaming response.

        Args:
            conversation_id: Conversation to add message to.
            collection_id: Collection to search for context.
            question: User's question.
            top_k: Number of chunks to retrieve.
            similarity_threshold: Minimum similarity score.
            system_prompt: Custom system prompt override.
            personality: Personality preset (professional, friendly, technical).
            temperature: LLM temperature setting.
            max_tokens: Maximum tokens for response.
            collection_name: Name of the collection for logging.

        Yields:
            Streaming response chunks.

        Raises:
            ValueError: If conversation or collection not found.
        """
        # Build agent config to save with the message
        agent_config = {
            "collection_name": collection_name,
            "personality": personality or "professional",
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_k": top_k,
            "system_prompt": system_prompt,
        }
        # Get conversation (verify it exists)
        conversation = await self.conv_repo.get_with_messages(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Get recent conversation history from cache (limit to last 6 messages for performance)
        cached_message_data = []
        if self.session_cache:
            cached_message_data = await self.session_cache.get_messages(
                str(conversation_id),
                limit=6,  # Keep last 3 exchanges (user+assistant pairs)
            )

        # Convert MessageData to ChatMessage (filter out timestamp field)
        messages: list[ChatMessage] = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in cached_message_data
        ]

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

        # Build context from chunks and prepare metadata for storage
        context = self._build_context(similar_chunks)
        context_chunks_data = self._build_context_metadata(similar_chunks)

        # Get the appropriate system prompt based on configuration
        base_prompt, custom_instructions = self._get_system_prompt(system_prompt, personality)

        # Detect language instruction and create prefix for user message
        lang_prefix = detect_language_prefix(custom_instructions)

        # Add user message to history (with lang prefix for LLM only)
        question_for_llm = f"{lang_prefix}{question}" if lang_prefix else question
        user_message = ChatMessage(role="user", content=question_for_llm)
        messages.append(user_message)

        # Save user message to DB (original question without prefix)
        user_db_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=question,
        )
        self.session.add(user_db_message)
        await self.session.flush()

        # Add user message to cache if available (original question)
        if self.session_cache:
            await self.session_cache.add_message(
                str(conversation_id),
                "user",
                question,
            )

        # Build full system content
        system_content = f"{base_prompt}\n\nContext:\n{context}"
        if custom_instructions:
            system_content += f"\n\n=== ADDITIONAL INSTRUCTIONS ===\n{custom_instructions}"

        # Only add default language instruction if custom prompt doesn't have one
        # This allows users to set specific language requirements in collection settings
        if not custom_instructions or not has_language_instruction(custom_instructions):
            system_content += LANGUAGE_INSTRUCTION

        # Add system message with context if not already there
        has_system = any(
            getattr(m, "role", None) == "system" or
            (isinstance(m, dict) and m.get("role") == "system")
            for m in messages
        )

        if not has_system:
            system_message = ChatMessage(
                role="system",
                content=system_content,
            )
            messages.insert(0, system_message)
        else:
            # Update system message with new context
            messages[0] = ChatMessage(
                role="system",
                content=system_content,
            )

        # Build full prompt string for debugging
        full_prompt = self._build_prompt_string(messages)

        # Generate streaming response
        response_content = ""
        tokens_input = None
        tokens_output = None
        start_time = time.time()

        async for chunk in self.llm_provider.generate_stream(messages):
            response_content += chunk.content
            yield chunk.content
            # Capture token counts from final chunk
            if chunk.is_final:
                tokens_input = chunk.tokens_input
                tokens_output = chunk.tokens_output

        latency_ms = int((time.time() - start_time) * 1000)

        # Yield sources metadata at the end (special marker for frontend)
        sources_json = json.dumps({"sources": context_chunks_data})
        yield f"\n[SOURCES]{sources_json}[/SOURCES]"

        # Calculate total tokens
        total_tokens = None
        if tokens_input is not None and tokens_output is not None:
            total_tokens = tokens_input + tokens_output

        # Save assistant message to DB
        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=response_content,
            prompt_input=full_prompt,
            context_chunks=context_chunks_data,
            agent_config=agent_config,
            latency_ms=latency_ms,
            model=self.llm_provider.provider_name,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_used=total_tokens,
        )
        self.session.add(assistant_message)
        await self.session.flush()

        # Update session cache with assistant message if cache is available
        if self.session_cache:
            await self.session_cache.add_message(
                str(conversation_id),
                "assistant",
                response_content,
            )

        # Commit transaction to persist messages to database
        await self.session.commit()

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
            similar_chunks: List of (chunk, similarity_score, filename) tuples.

        Returns:
            Formatted context string.
        """
        if not similar_chunks:
            return "No relevant context found."

        context_parts = []
        for chunk, score, filename in similar_chunks:
            context_parts.append(
                f"[Document: {filename} (relevance: {score:.2%})]\n"
                f"{chunk.content}\n"
            )

        return "\n".join(context_parts)

    def _build_context_metadata(
        self,
        similar_chunks: list[tuple],
    ) -> list[dict]:
        """Build metadata for similar chunks, grouped by filename with highest score.

        Args:
            similar_chunks: List of (chunk, similarity_score, filename) tuples.

        Returns:
            List of unique filenames with their highest similarity score.
        """
        if not similar_chunks:
            return []

        # Group by filename and keep highest score
        file_scores: dict[str, float] = {}
        for chunk, score, filename in similar_chunks:
            if filename not in file_scores or score > file_scores[filename]:
                file_scores[filename] = score

        # Sort by score descending
        sorted_files = sorted(file_scores.items(), key=lambda x: x[1], reverse=True)

        return [
            {
                "filename": filename,
                "similarity_score": round(score, 4),
            }
            for filename, score in sorted_files
        ]

    def _build_prompt_string(self, messages: list[ChatMessage]) -> str:
        """Build a readable prompt string from messages for debugging.

        Args:
            messages: List of chat messages.

        Returns:
            Formatted prompt string.
        """
        parts = []
        for msg in messages:
            role = msg.get("role", "unknown") if isinstance(msg, dict) else getattr(msg, "role", "unknown")
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            parts.append(f"=== {role.upper()} ===\n{content}")
        return "\n\n".join(parts)
