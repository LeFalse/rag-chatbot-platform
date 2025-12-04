"""Integration tests for document endpoints validation."""

from io import BytesIO
from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestDocumentsEndpoints:
    """Test document endpoint functionality."""

    @pytest.mark.asyncio
    async def test_create_collection(self, api_client: AsyncClient):
        """Test creating a new collection."""
        response = await api_client.post(
            "/documents/collections",
            json={
                "name": "test-collection",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-collection"
        assert data["embedding_model"] == "nomic-embed-text"
        assert data["embedding_dimension"] == 768
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_collections(self, api_client: AsyncClient):
        """Test listing all collections."""
        # Create a collection first
        create_response = await api_client.post(
            "/documents/collections",
            json={
                "name": "test-for-listing",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
            },
        )
        assert create_response.status_code == 200
        created_id = create_response.json()["id"]

        response = await api_client.get("/documents/collections")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Verify our created collection is in the list
        collection_ids = [c["id"] for c in data]
        assert created_id in collection_ids

    @pytest.mark.asyncio
    async def test_list_documents_in_collection(
        self, api_client: AsyncClient
    ):
        """Test listing documents in a collection."""
        # Create a collection first
        create_response = await api_client.post(
            "/documents/collections",
            json={
                "name": "test-for-docs",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
            },
        )
        assert create_response.status_code == 200
        collection_id = create_response.json()["id"]

        response = await api_client.get(f"/documents/{collection_id}")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_upload_document(
        self, api_client: AsyncClient
    ):
        """Test uploading a document to a collection."""
        # Create a collection first
        create_response = await api_client.post(
            "/documents/collections",
            json={
                "name": "test-for-upload",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
            },
        )
        assert create_response.status_code == 200
        collection_id = create_response.json()["id"]

        file_content = b"Test document content for RAG system"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}

        response = await api_client.post(
            f"/documents/{collection_id}/upload",
            files=files,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.txt"
        assert "id" in data
        assert data["collection_id"] == collection_id

    @pytest.mark.asyncio
    async def test_delete_document(
        self, api_client: AsyncClient
    ):
        """Test deleting a document."""
        # Create a collection first
        create_response = await api_client.post(
            "/documents/collections",
            json={
                "name": "test-for-delete",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
            },
        )
        assert create_response.status_code == 200
        collection_id = create_response.json()["id"]

        # Upload a document
        file_content = b"Test document for deletion"
        files = {"file": ("delete_test.txt", BytesIO(file_content), "text/plain")}

        upload_response = await api_client.post(
            f"/documents/{collection_id}/upload",
            files=files,
        )

        assert upload_response.status_code == 200
        document_id = upload_response.json()["id"]

        # Now delete it
        delete_response = await api_client.delete(f"/documents/{document_id}")

        assert delete_response.status_code == 200
        data = delete_response.json()
        assert data["message"] == "Document deleted successfully"

    @pytest.mark.asyncio
    async def test_upload_to_nonexistent_collection(self, api_client: AsyncClient):
        """Test uploading to a non-existent collection returns 404."""
        fake_id = uuid4()
        file_content = b"Test document"
        files = {"file": ("test.txt", BytesIO(file_content), "text/plain")}

        response = await api_client.post(
            f"/documents/{fake_id}/upload",
            files=files,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self, api_client: AsyncClient):
        """Test deleting a non-existent document is idempotent (returns 200)."""
        fake_id = uuid4()

        response = await api_client.delete(f"/documents/{fake_id}")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_collection(self, api_client: AsyncClient):
        """Test deleting a collection and all its documents."""
        # Create a collection
        create_response = await api_client.post(
            "/documents/collections",
            json={
                "name": "test-for-collection-delete",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
            },
        )
        assert create_response.status_code == 200
        collection_id = create_response.json()["id"]

        # Upload a document
        file_content = b"Test document in collection to be deleted"
        files = {"file": ("collection_delete_test.txt", BytesIO(file_content), "text/plain")}
        upload_response = await api_client.post(
            f"/documents/{collection_id}/upload",
            files=files,
        )
        assert upload_response.status_code == 200

        # Delete the collection
        delete_response = await api_client.delete(f"/documents/collections/{collection_id}")
        assert delete_response.status_code == 200
        data = delete_response.json()
        assert data["message"] == "Collection deleted successfully"

        # Verify collection is gone (should return empty list or not contain this collection)
        list_response = await api_client.get("/documents/collections")
        assert list_response.status_code == 200
        collection_ids = [c["id"] for c in list_response.json()]
        assert collection_id not in collection_ids

    @pytest.mark.asyncio
    async def test_delete_nonexistent_collection(self, api_client: AsyncClient):
        """Test deleting a non-existent collection is idempotent (returns 200)."""
        fake_id = uuid4()

        response = await api_client.delete(f"/documents/collections/{fake_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Collection deleted successfully"

    @pytest.mark.asyncio
    async def test_update_collection_config(self, api_client: AsyncClient):
        """Test updating a collection's agent configuration."""
        # Create a collection first
        create_response = await api_client.post(
            "/documents/collections",
            json={
                "name": "test-collection-config",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
            },
        )
        assert create_response.status_code == 200
        collection_id = create_response.json()["id"]

        # Verify default values
        data = create_response.json()
        assert data["personality"] == "professional"
        assert data["temperature"] == 0.5
        assert data["max_tokens"] == 512
        assert data["top_k"] == 5
        assert data["system_prompt"] is None

        # Update collection config
        update_response = await api_client.put(
            f"/documents/collections/{collection_id}",
            json={
                "name": "updated-collection-name",
                "description": "A test collection with custom config",
                "personality": "friendly",
                "temperature": 0.7,
                "max_tokens": 1024,
                "top_k": 10,
            },
        )
        assert update_response.status_code == 200
        updated_data = update_response.json()

        # Verify updates
        assert updated_data["name"] == "updated-collection-name"
        assert updated_data["description"] == "A test collection with custom config"
        assert updated_data["personality"] == "friendly"
        assert updated_data["temperature"] == 0.7
        assert updated_data["max_tokens"] == 1024
        assert updated_data["top_k"] == 10

    @pytest.mark.asyncio
    async def test_update_collection_with_custom_prompt(self, api_client: AsyncClient):
        """Test updating a collection with a custom system prompt."""
        # Create a collection first
        create_response = await api_client.post(
            "/documents/collections",
            json={
                "name": "test-custom-prompt",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
            },
        )
        assert create_response.status_code == 200
        collection_id = create_response.json()["id"]

        custom_prompt = "You are a helpful assistant specialized in Python programming."

        # Update with custom prompt
        update_response = await api_client.put(
            f"/documents/collections/{collection_id}",
            json={
                "personality": "custom",
                "system_prompt": custom_prompt,
            },
        )
        assert update_response.status_code == 200
        data = update_response.json()

        assert data["personality"] == "custom"
        assert data["system_prompt"] == custom_prompt

    @pytest.mark.asyncio
    async def test_update_nonexistent_collection(self, api_client: AsyncClient):
        """Test updating a non-existent collection returns 404."""
        fake_id = uuid4()

        response = await api_client.put(
            f"/documents/collections/{fake_id}",
            json={"name": "new-name"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_collection_config_persists_after_listing(self, api_client: AsyncClient):
        """Test that collection config is returned in list endpoint."""
        # Create a collection with custom config
        create_response = await api_client.post(
            "/documents/collections",
            json={
                "name": "test-config-in-list",
                "embedding_model": "nomic-embed-text",
                "embedding_dimension": 768,
            },
        )
        assert create_response.status_code == 200
        collection_id = create_response.json()["id"]

        # Update config
        await api_client.put(
            f"/documents/collections/{collection_id}",
            json={
                "personality": "technical",
                "temperature": 0.3,
            },
        )

        # List collections and verify config is included
        list_response = await api_client.get("/documents/collections")
        assert list_response.status_code == 200

        collections = list_response.json()
        our_collection = next(c for c in collections if c["id"] == collection_id)

        assert our_collection["personality"] == "technical"
        assert our_collection["temperature"] == 0.3
