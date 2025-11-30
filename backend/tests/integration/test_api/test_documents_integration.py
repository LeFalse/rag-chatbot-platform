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
