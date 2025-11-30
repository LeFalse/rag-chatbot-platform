"""Chat and conversation routes."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.conversation import Conversation
from app.schemas.requests.schemas import AskQuestionRequest, CreateConversationRequest
from app.schemas.responses.schemas import ConversationResponse, ConversationHistoryResponse, MessageResponse
from app.services.chat_service import ChatService
from app.services.embedding_service import EmbeddingService
from app.services.cache.embedding_cache import EmbeddingCache
from app.services.cache.session_cache import SessionCache
from app.services.cache.redis_client import get_redis_client
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.message_repo import MessageRepository
from app.providers.llm.factory import create_llm_provider
from app.providers.embedding.factory import create_embedding_provider

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


@router.post("/conversations/{conversation_id}/ask")
async def ask_question(
    conversation_id: str,
    request: AskQuestionRequest,
    session: AsyncSession = Depends(get_session),
):
    """Ask a question in a conversation with streaming response."""
    try:
        conv_uuid = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID format")

    try:
        # Get conversation to extract collection_id
        conv_repo = ConversationRepository(session)
        conversation = await conv_repo.get_with_messages(conv_uuid)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        llm_provider = create_llm_provider(request.llm_provider)
        embedding_provider = create_embedding_provider()
        redis_client = await get_redis_client()
        embedding_cache = EmbeddingCache(redis_client)
        session_cache = SessionCache(redis_client)

        # Ensure session cache exists for this conversation
        if not await session_cache.session_exists(conversation_id):
            await session_cache.create_session(
                conversation_id,
                str(conversation.collection_id),
            )

        embedding_service = EmbeddingService(session, embedding_provider, embedding_cache)
        service = ChatService(
            session,
            llm_provider,
            embedding_provider,
            embedding_service,
            session_cache,
        )

        async def generate():
            """Generate streaming responses."""
            try:
                async for chunk in service.answer_question(
                    conv_uuid,
                    conversation.collection_id,
                    request.question,
                    top_k=request.top_k,
                    similarity_threshold=request.similarity_threshold,
                ):
                    yield chunk
            except Exception as e:
                yield f"Error: {str(e)}"

        return StreamingResponse(generate(), media_type="text/event-stream")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
