"""Chat and conversation routes."""

import logging
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, get_session
from app.mcp.gitlab import GitLabConfig
from app.models.conversation import Conversation
from app.providers.embedding.factory import create_embedding_provider
from app.providers.llm.factory import create_llm_provider
from app.repositories.collection_repo import CollectionRepository
from app.repositories.conversation_repo import ConversationRepository
from app.schemas.requests.schemas import AskQuestionRequest, CreateConversationRequest
from app.schemas.responses.schemas import (
    ConversationHistoryResponse,
    ConversationResponse,
    MessageResponse,
)
from app.services.agent_service import AgentService, MCPConfig
from app.services.cache.embedding_cache import EmbeddingCache
from app.services.cache.redis_client import get_redis_client
from app.services.cache.session_cache import SessionCache
from app.services.chat_service import ChatService
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/conversations")
async def create_conversation(
    request: CreateConversationRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new conversation."""
    try:
        collection_uuid = UUID(request.collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID format")

    try:
        repo = ConversationRepository(session)
        conversation_obj = Conversation(
            collection_id=collection_uuid,
            title=request.title,
        )
        conversation = await repo.create(conversation_obj)

        # Initialize session cache for the new conversation
        redis_client = await get_redis_client()
        session_cache = SessionCache(redis_client)
        await session_cache.create_session(
            str(conversation.id),
            str(collection_uuid),
        )

        return ConversationResponse(
            id=str(conversation.id),
            collection_id=str(conversation.collection_id),
            title=conversation.title,
            message_count=0,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def list_conversations(
    collection_id: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """List conversations in a collection."""
    try:
        collection_uuid = UUID(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID format")

    try:
        repo = ConversationRepository(session)
        conversations = await repo.get_by_collection(collection_uuid)
        return [
            ConversationResponse(
                id=str(c.id),
                collection_id=str(c.collection_id),
                title=c.title,
                message_count=0,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in conversations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get conversation history."""
    try:
        conv_uuid = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

    try:
        llm_provider = create_llm_provider()
        embedding_provider = create_embedding_provider()
        redis_client = await get_redis_client()
        embedding_cache = EmbeddingCache(redis_client)
        session_cache = SessionCache(redis_client)
        embedding_service = EmbeddingService(session, embedding_provider, embedding_cache)
        service = ChatService(
            session,
            llm_provider,
            embedding_provider,
            embedding_service,
            session_cache,
        )

        messages_list = await service.get_conversation_history(conv_uuid)
        messages = [
            MessageResponse(
                id=msg.get("id", ""),
                role=msg["role"],
                content=msg["content"],
                created_at=msg.get("created_at", ""),
                latency_ms=msg.get("latency_ms"),
                model=msg.get("model"),
            )
            for msg in messages_list
        ]

        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            messages=messages,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _build_mcp_config(collection_mcp_config: dict | None) -> MCPConfig | None:
    """Build MCPConfig from collection's mcp_config.

    Args:
        collection_mcp_config: Raw MCP config from collection.

    Returns:
        MCPConfig if GitLab is enabled, None otherwise.
    """
    if not collection_mcp_config:
        return None

    gitlab_config = collection_mcp_config.get("gitlab")
    if not gitlab_config or not gitlab_config.get("enabled", True):
        return None

    # Build GitLabConfig for MCP client
    # Token is retrieved from environment variable for security
    gitlab_token = os.environ.get("GITLAB_TOKEN", "")

    if not gitlab_token:
        logger.warning("GITLAB_TOKEN not set, MCP GitLab tools will not work")
        return None

    return MCPConfig(
        gitlab=GitLabConfig(
            gitlab_url=gitlab_config.get("gitlab_url", "https://gitlab.com"),
            token=gitlab_token,
            project_id=gitlab_config.get("project_id", ""),
        )
    )


@router.post("/conversations/{conversation_id}/ask")
async def ask_question(
    conversation_id: str,
    request: AskQuestionRequest,
):
    """Ask a question in a conversation with streaming response.

    If the collection has MCP configured (e.g., GitLab integration),
    uses the AgentService with tool calling. Otherwise uses regular
    ChatService for RAG-only responses.

    NOTE: Session is created inside the generator to ensure proper lifecycle
    management with streaming responses. Using Depends(get_session) would
    cause the session to close before the generator finishes.
    """
    try:
        conv_uuid = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

    # Validate conversation and collection exist before starting stream
    # Use a short-lived session for validation only
    async with AsyncSessionLocal() as validation_session:
        conv_repo = ConversationRepository(validation_session)
        conversation = await conv_repo.get_with_messages(conv_uuid)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        collection_repo = CollectionRepository(validation_session)
        collection = await collection_repo.get_by_id(conversation.collection_id)
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        # Extract needed values before session closes
        collection_id = conversation.collection_id
        collection_temperature = collection.temperature
        collection_max_tokens = collection.max_tokens
        collection_top_k = collection.top_k
        collection_system_prompt = collection.system_prompt
        collection_personality = collection.personality
        collection_name = collection.name
        collection_mcp_config = collection.mcp_config

    # Create providers (don't need session)
    llm_provider = create_llm_provider(
        request.llm_provider,
        temperature=collection_temperature,
        max_tokens=collection_max_tokens,
    )
    embedding_provider = create_embedding_provider()

    # Use collection's top_k if not overridden in request (default is 5)
    effective_top_k = collection_top_k if request.top_k == 5 else request.top_k

    # Check if MCP is configured for agent mode
    mcp_config = _build_mcp_config(collection_mcp_config)

    logger.debug(
        "MCP check: collection.mcp_config=%s, mcp_config=%s, supports_tool_calling=%s",
        collection_mcp_config,
        mcp_config,
        llm_provider.supports_tool_calling,
    )

    if mcp_config and llm_provider.supports_tool_calling:
        # Use AgentService with tool calling
        logger.info(
            "Using agent mode for conversation %s (MCP enabled)",
            conversation_id,
        )

        async def generate_agent():
            """Generate streaming responses from agent.

            Session is created here to ensure it lives for the entire
            duration of the streaming response.
            """
            async with AsyncSessionLocal() as session:
                try:
                    redis_client = await get_redis_client()
                    embedding_cache = EmbeddingCache(redis_client)
                    session_cache = SessionCache(redis_client)

                    # Ensure session cache exists for this conversation
                    if not await session_cache.session_exists(conversation_id):
                        await session_cache.create_session(
                            conversation_id,
                            str(collection_id),
                        )

                    embedding_service = EmbeddingService(session, embedding_provider, embedding_cache)

                    agent_service = AgentService(
                        session,
                        llm_provider,
                        embedding_service,
                        session_cache,
                    )

                    async for chunk in agent_service.run_agent(
                        conv_uuid,
                        collection_id,
                        request.question,
                        mcp_config=mcp_config,
                        top_k=effective_top_k,
                        similarity_threshold=request.similarity_threshold,
                        temperature=collection_temperature,
                        max_tokens=collection_max_tokens,
                        collection_name=collection_name,
                        personality=collection_personality,
                        system_prompt=collection_system_prompt,
                    ):
                        yield chunk

                    await session.commit()
                except NotImplementedError as e:
                    logger.warning("Agent mode failed, falling back to chat: %s", e)
                    yield f"Error: {e}"
                except Exception as e:
                    logger.exception("Agent error")
                    await session.rollback()
                    yield f"Error: {e}"

        return StreamingResponse(generate_agent(), media_type="text/event-stream")

    else:
        # Use regular ChatService (RAG only)
        async def generate_chat():
            """Generate streaming responses from chat service.

            Session is created here to ensure it lives for the entire
            duration of the streaming response.
            """
            async with AsyncSessionLocal() as session:
                try:
                    redis_client = await get_redis_client()
                    embedding_cache = EmbeddingCache(redis_client)
                    session_cache = SessionCache(redis_client)

                    # Ensure session cache exists for this conversation
                    if not await session_cache.session_exists(conversation_id):
                        await session_cache.create_session(
                            conversation_id,
                            str(collection_id),
                        )

                    embedding_service = EmbeddingService(session, embedding_provider, embedding_cache)

                    service = ChatService(
                        session,
                        llm_provider,
                        embedding_provider,
                        embedding_service,
                        session_cache,
                    )

                    async for chunk in service.answer_question(
                        conv_uuid,
                        collection_id,
                        request.question,
                        top_k=effective_top_k,
                        similarity_threshold=request.similarity_threshold,
                        system_prompt=collection_system_prompt,
                        personality=collection_personality,
                        temperature=collection_temperature,
                        max_tokens=collection_max_tokens,
                        collection_name=collection_name,
                    ):
                        yield chunk

                    await session.commit()
                except Exception as e:
                    logger.exception("Chat error")
                    await session.rollback()
                    yield f"Error: {e}"

        return StreamingResponse(generate_chat(), media_type="text/event-stream")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a conversation (idempotent)."""
    try:
        conv_uuid = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

    try:
        repo = ConversationRepository(session)
        conversation = await repo.get_by_id(conv_uuid)
        if conversation:
            await repo.delete(conv_uuid)
        return {"message": "Conversation deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
