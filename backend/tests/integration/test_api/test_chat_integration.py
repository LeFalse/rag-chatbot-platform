"""Integration tests for chat endpoints validation."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.collection import Collection


class TestChatEndpoints:
    """Test chat endpoint functionality."""

    @pytest.mark.asyncio
    async def test_create_conversation(
        self, api_client: AsyncClient
    ):
        """Test creating a new conversation."""
        # Create a collection first
        coll_response = await api_client.post(
            "/documents/collections",
            json={
                "name": "test-coll-conv",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
            },
        )
        assert coll_response.status_code == 200
        collection_id = coll_response.json()["id"]

        response = await api_client.post(
            "/chat/conversations",
            json={
                "collection_id": collection_id,
                "title": "Test conversation",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test conversation"
        assert data["collection_id"] == collection_id
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_conversations_in_collection(
        self, api_client: AsyncClient
    ):
        """Test listing conversations in a collection."""
        # Create a collection first
        coll_response = await api_client.post(
            "/documents/collections",
            json={
                "name": "test-coll-list",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
            },
        )
        assert coll_response.status_code == 200
        collection_id = coll_response.json()["id"]

        # Create a conversation
        create_response = await api_client.post(
            "/chat/conversations",
            json={
                "collection_id": collection_id,
                "title": "Test conversation for listing",
            },
        )
        assert create_response.status_code == 200
        created_id = create_response.json()["id"]

        response = await api_client.get(
            f"/chat/conversations",
            params={"collection_id": collection_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Verify our created conversation is in the list
        conversation_ids = [c["id"] for c in data]
        assert created_id in conversation_ids

    @pytest.mark.asyncio
    async def test_get_conversation_history(
        self, api_client: AsyncClient
    ):
        """Test retrieving conversation history."""
        # Create a collection first
        coll_response = await api_client.post(
            "/documents/collections",
            json={
                "name": "test-coll-hist",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
            },
        )
        assert coll_response.status_code == 200
        collection_id = coll_response.json()["id"]

        # Create a conversation
        create_response = await api_client.post(
            "/chat/conversations",
            json={
                "collection_id": collection_id,
                "title": "Test conversation for history",
            },
        )
        assert create_response.status_code == 200
        conversation_id = create_response.json()["id"]

        response = await api_client.get(
            f"/chat/conversations/{conversation_id}/history"
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "conversation_id" in data
        assert "messages" in data
        assert isinstance(data["messages"], list)

    @pytest.mark.asyncio
    async def test_delete_conversation(
        self, api_client: AsyncClient
    ):
        """Test deleting a conversation."""
        # Create a collection first
        coll_response = await api_client.post(
            "/documents/collections",
            json={
                "name": "test-coll-del",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
            },
        )
        assert coll_response.status_code == 200
        collection_id = coll_response.json()["id"]

        # Create a conversation
        create_response = await api_client.post(
            "/chat/conversations",
            json={
                "collection_id": collection_id,
                "title": "To be deleted",
            },
        )

        assert create_response.status_code == 200
        conversation_id = create_response.json()["id"]

        # Now delete it
        delete_response = await api_client.delete(
            f"/chat/conversations/{conversation_id}"
        )

        assert delete_response.status_code == 200
        data = delete_response.json()
        assert data["message"] == "Conversation deleted successfully"

    @pytest.mark.asyncio
    async def test_delete_nonexistent_conversation(self, api_client: AsyncClient):
        """Test deleting a non-existent conversation is idempotent (returns 200)."""
        fake_id = uuid4()

        response = await api_client.delete(f"/chat/conversations/{fake_id}")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ask_question_streaming(
        self, api_client: AsyncClient, api_test_collection: Collection
    ):
        """Test asking a question with streaming response."""
        # Create a conversation first
        create_response = await api_client.post(
            "/chat/conversations",
            json={
                "collection_id": str(api_test_collection.id),
                "title": "Test conversation for asking",
            },
        )
        assert create_response.status_code == 200
        conversation_id = create_response.json()["id"]

        response = await api_client.post(
            f"/chat/conversations/{conversation_id}/ask",
            json={"question": "What is RAG?"},
        )

        assert response.status_code == 200
        # Streaming response should have content
        assert len(response.content) > 0
