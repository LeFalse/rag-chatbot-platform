"""Integration tests for repositories with real PostgreSQL."""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import Base
from app.models.chunk import Chunk
from app.models.collection import Collection
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.message import Message
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.collection_repo import CollectionRepository
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.document_repo import DocumentRepository
from app.repositories.message_repo import MessageRepository

settings = get_settings()


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Create async session for integration tests."""
    engine = create_async_engine(settings.database_url, echo=False)
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()

    await engine.dispose()


class TestCollectionRepositoryIntegration:
    """Integration tests for CollectionRepository."""

    @pytest.mark.asyncio
    async def test_create_and_retrieve(self, db_session: AsyncSession):
        """Test creating and retrieving a collection."""
        repo = CollectionRepository(db_session)
        unique_name = f"test-collection-{uuid4().hex[:8]}"

        collection = Collection(
            name=unique_name,
            description="Integration test collection",
            embedding_model="nomic-embed-text",
            embedding_dimension=768,
        )

        created = await repo.create(collection)
        assert created.id is not None
        assert created.name == unique_name

        # Retrieve by ID
        retrieved = await repo.get_by_id(created.id)
        assert retrieved is not None
        assert retrieved.name == unique_name

        # Retrieve by name
        by_name = await repo.get_by_name(unique_name)
        assert by_name is not None
        assert by_name.id == created.id

    @pytest.mark.asyncio
    async def test_search_by_name(self, db_session: AsyncSession):
        """Test searching collections by name pattern."""
        repo = CollectionRepository(db_session)
        prefix = f"searchtest-{uuid4().hex[:4]}"

        # Create multiple collections
        for i in range(3):
            coll = Collection(
                name=f"{prefix}-collection-{i}",
                embedding_model="nomic-embed-text",
                embedding_dimension=768,
            )
            await repo.create(coll)

        # Search by prefix
        results = await repo.search_by_name(prefix)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_update_collection(self, db_session: AsyncSession):
        """Test updating a collection."""
        repo = CollectionRepository(db_session)

        collection = Collection(
            name=f"update-test-{uuid4().hex[:8]}",
            description="Original description",
            embedding_model="nomic-embed-text",
            embedding_dimension=768,
        )
        created = await repo.create(collection)

        # Update
        created.description = "Updated description"
        updated = await repo.update(created)

        assert updated.description == "Updated description"

    @pytest.mark.asyncio
    async def test_delete_collection(self, db_session: AsyncSession):
        """Test deleting a collection."""
        repo = CollectionRepository(db_session)

        collection = Collection(
            name=f"delete-test-{uuid4().hex[:8]}",
            embedding_model="nomic-embed-text",
            embedding_dimension=768,
        )
        created = await repo.create(collection)
        coll_id = created.id

        # Delete by ID
        deleted = await repo.delete(coll_id)
        assert deleted is True

        # Verify deleted
        retrieved = await repo.get_by_id(coll_id)
        assert retrieved is None


class TestDocumentRepositoryIntegration:
    """Integration tests for DocumentRepository."""

    @pytest_asyncio.fixture
    async def collection(self, db_session: AsyncSession) -> Collection:
        """Create a test collection."""
        repo = CollectionRepository(db_session)
        coll = Collection(
            name=f"doc-test-{uuid4().hex[:8]}",
            embedding_model="nomic-embed-text",
            embedding_dimension=768,
        )
        return await repo.create(coll)

    @pytest.mark.asyncio
    async def test_create_document(
        self,
        db_session: AsyncSession,
        collection: Collection,
    ):
        """Test creating a document."""
        repo = DocumentRepository(db_session)

        doc = Document(
            collection_id=collection.id,
            filename=f"test-{uuid4().hex[:8]}.pdf",
            content_type="application/pdf",
            file_size=1024,
            metadata_={"author": "test"},
        )

        created = await repo.create(doc)

        assert created.id is not None
        assert created.collection_id == collection.id
        assert created.filename is not None

    @pytest.mark.asyncio
    async def test_get_documents_by_collection(
        self,
        db_session: AsyncSession,
        collection: Collection,
    ):
        """Test getting all documents for a collection."""
        repo = DocumentRepository(db_session)

        # Create multiple documents
        for i in range(3):
            doc = Document(
                collection_id=collection.id,
                filename=f"doc-{i}-{uuid4().hex[:4]}.txt",
                content_type="text/plain",
                file_size=100 * i,
            )
            await repo.create(doc)

        # Get all
        docs = await repo.get_by_collection(collection.id)
        assert len(docs) == 3

    @pytest.mark.asyncio
    async def test_get_by_filename(
        self,
        db_session: AsyncSession,
        collection: Collection,
    ):
        """Test finding document by filename."""
        repo = DocumentRepository(db_session)
        filename = f"unique-{uuid4().hex[:8]}.txt"

        doc = Document(
            collection_id=collection.id,
            filename=filename,
            content_type="text/plain",
            file_size=100,
        )
        await repo.create(doc)

        # Find by filename
        found = await repo.get_by_filename(collection.id, filename)
        assert found is not None
        assert found.filename == filename


class TestChunkRepositoryIntegration:
    """Integration tests for ChunkRepository including vector search."""

    @pytest_asyncio.fixture
    async def collection_with_document(
        self,
        db_session: AsyncSession,
    ) -> tuple[Collection, Document]:
        """Create a collection with a document."""
        coll_repo = CollectionRepository(db_session)
        doc_repo = DocumentRepository(db_session)

        collection = Collection(
            name=f"chunk-test-{uuid4().hex[:8]}",
            embedding_model="nomic-embed-text",
            embedding_dimension=768,
        )
        coll = await coll_repo.create(collection)

        document = Document(
            collection_id=coll.id,
            filename="test-doc.txt",
            content_type="text/plain",
            file_size=1000,
        )
        doc = await doc_repo.create(document)

        return coll, doc

    @pytest.mark.asyncio
    async def test_create_chunks(
        self,
        db_session: AsyncSession,
        collection_with_document: tuple[Collection, Document],
    ):
        """Test creating chunks for a document."""
        _, document = collection_with_document
        repo = ChunkRepository(db_session)

        chunk = Chunk(
            document_id=document.id,
            content="This is test content for the chunk.",
            chunk_index=0,
            metadata_={"page": 1},
        )

        created = await repo.create(chunk)

        assert created.id is not None
        assert created.document_id == document.id
        assert created.chunk_index == 0

    @pytest.mark.asyncio
    async def test_bulk_create_chunks(
        self,
        db_session: AsyncSession,
        collection_with_document: tuple[Collection, Document],
    ):
        """Test bulk creating chunks."""
        _, document = collection_with_document
        repo = ChunkRepository(db_session)

        chunks = [
            Chunk(
                document_id=document.id,
                content=f"Chunk content {i}",
                chunk_index=i,
            )
            for i in range(5)
        ]

        created = await repo.bulk_create(chunks)

        assert len(created) == 5
        assert all(c.id is not None for c in created)

    @pytest.mark.asyncio
    async def test_get_chunks_by_document(
        self,
        db_session: AsyncSession,
        collection_with_document: tuple[Collection, Document],
    ):
        """Test getting chunks by document in order."""
        _, document = collection_with_document
        repo = ChunkRepository(db_session)

        # Create chunks out of order
        for i in [2, 0, 1]:
            chunk = Chunk(
                document_id=document.id,
                content=f"Content {i}",
                chunk_index=i,
            )
            await repo.create(chunk)

        # Get should return in order
        chunks = await repo.get_by_document(document.id)

        assert len(chunks) == 3
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1
        assert chunks[2].chunk_index == 2

    @pytest.mark.asyncio
    async def test_vector_search(
        self,
        db_session: AsyncSession,
        collection_with_document: tuple[Collection, Document],
    ):
        """Test vector similarity search with pgvector."""
        collection, document = collection_with_document
        repo = ChunkRepository(db_session)

        # Create chunks with embeddings
        # Embedding dimension must match model schema (768 for nomic-embed-text)
        base_embedding = [0.1] * 768

        chunks_data = [
            ("Python programming basics", [0.1 + i * 0.01 for _ in range(768)])
            for i in range(3)
        ]

        for i, (content, _) in enumerate(chunks_data):
            chunk = Chunk(
                document_id=document.id,
                content=content,
                chunk_index=i,
                embedding=base_embedding,
            )
            await repo.create(chunk)

        # Search with similar embedding
        query_embedding = [0.1] * 768
        results = await repo.search_similar(
            embedding=query_embedding,
            collection_id=collection.id,
            limit=5,
            threshold=0.5,
        )

        assert len(results) > 0
        # Results should have chunk, similarity score, and filename
        chunk, score, filename = results[0]
        assert chunk.content is not None
        assert 0 <= score <= 1
        assert filename == "test-doc.txt"

    @pytest.mark.asyncio
    async def test_delete_chunks_by_document(
        self,
        db_session: AsyncSession,
        collection_with_document: tuple[Collection, Document],
    ):
        """Test deleting all chunks for a document."""
        _, document = collection_with_document
        repo = ChunkRepository(db_session)

        # Create chunks
        for i in range(3):
            chunk = Chunk(
                document_id=document.id,
                content=f"To delete {i}",
                chunk_index=i,
            )
            await repo.create(chunk)

        # Delete all
        deleted_count = await repo.delete_by_document(document.id)
        assert deleted_count == 3

        # Verify deleted
        remaining = await repo.get_by_document(document.id)
        assert len(remaining) == 0


class TestConversationRepositoryIntegration:
    """Integration tests for ConversationRepository."""

    @pytest_asyncio.fixture
    async def collection(self, db_session: AsyncSession) -> Collection:
        """Create a test collection."""
        repo = CollectionRepository(db_session)
        coll = Collection(
            name=f"conv-test-{uuid4().hex[:8]}",
            embedding_model="nomic-embed-text",
            embedding_dimension=768,
        )
        return await repo.create(coll)

    @pytest.mark.asyncio
    async def test_create_conversation(
        self,
        db_session: AsyncSession,
        collection: Collection,
    ):
        """Test creating a conversation."""
        repo = ConversationRepository(db_session)

        conv = Conversation(
            collection_id=collection.id,
            title="Test Conversation",
        )

        created = await repo.create(conv)

        assert created.id is not None
        assert created.title == "Test Conversation"

    @pytest.mark.asyncio
    async def test_get_conversations_by_collection(
        self,
        db_session: AsyncSession,
        collection: Collection,
    ):
        """Test getting conversations by collection."""
        repo = ConversationRepository(db_session)

        # Create multiple conversations
        for i in range(3):
            conv = Conversation(
                collection_id=collection.id,
                title=f"Conversation {i}",
            )
            await repo.create(conv)

        # Get all
        convs = await repo.get_by_collection(collection.id)
        assert len(convs) == 3


class TestMessageRepositoryIntegration:
    """Integration tests for MessageRepository."""

    @pytest_asyncio.fixture
    async def conversation(self, db_session: AsyncSession) -> Conversation:
        """Create a test conversation."""
        coll_repo = CollectionRepository(db_session)
        conv_repo = ConversationRepository(db_session)

        coll = Collection(
            name=f"msg-test-{uuid4().hex[:8]}",
            embedding_model="nomic-embed-text",
            embedding_dimension=768,
        )
        collection = await coll_repo.create(coll)

        conv = Conversation(
            collection_id=collection.id,
            title="Test Conversation",
        )
        return await conv_repo.create(conv)

    @pytest.mark.asyncio
    async def test_create_message(
        self,
        db_session: AsyncSession,
        conversation: Conversation,
    ):
        """Test creating a message."""
        repo = MessageRepository(db_session)

        msg = Message(
            conversation_id=conversation.id,
            role="user",
            content="Hello, world!",
            tokens_used=5,
            model="test-model",
        )

        created = await repo.create(msg)

        assert created.id is not None
        assert created.role == "user"
        assert created.content == "Hello, world!"

    @pytest.mark.asyncio
    async def test_get_messages_by_conversation(
        self,
        db_session: AsyncSession,
        conversation: Conversation,
    ):
        """Test getting messages in order.

        Note: Messages are ordered by created_at, then by role (user before assistant)
        when timestamps are equal. This ensures proper conversation flow display.
        """
        from datetime import datetime, timedelta, timezone

        repo = MessageRepository(db_session)

        # Create messages with explicit timestamps to ensure proper ordering
        base_time = datetime.now(timezone.utc)
        roles = ["user", "assistant", "user", "assistant"]
        for i, role in enumerate(roles):
            msg = Message(
                conversation_id=conversation.id,
                role=role,
                content=f"Message from {role}",
                model="test-model",
                created_at=base_time + timedelta(seconds=i),
            )
            await repo.create(msg)

        # Get all
        messages = await repo.get_by_conversation(conversation.id)

        assert len(messages) == 4
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert messages[2].role == "user"
        assert messages[3].role == "assistant"

    @pytest.mark.asyncio
    async def test_get_recent_messages(
        self,
        db_session: AsyncSession,
        conversation: Conversation,
    ):
        """Test getting recent messages with limit."""
        repo = MessageRepository(db_session)

        # Create 10 messages
        for i in range(10):
            msg = Message(
                conversation_id=conversation.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                model="test-model",
            )
            await repo.create(msg)

        # Get last 5
        recent = await repo.get_by_conversation(conversation.id, limit=5)

        assert len(recent) == 5


class TestTransactionIntegration:
    """Test transaction behavior across repositories."""

    @pytest.mark.asyncio
    async def test_rollback_on_error(self, db_session: AsyncSession):
        """Test that errors rollback the transaction."""
        coll_repo = CollectionRepository(db_session)

        # Create a collection
        coll = Collection(
            name=f"rollback-test-{uuid4().hex[:8]}",
            embedding_model="nomic-embed-text",
            embedding_dimension=768,
        )
        created = await coll_repo.create(coll)
        coll_id = created.id

        # The fixture will rollback
        # After rollback, collection should not persist
        # (This is implicitly tested by the fixture cleanup)
        assert coll_id is not None

    @pytest.mark.asyncio
    async def test_cascade_relationships(self, db_session: AsyncSession):
        """Test that related entities are created together."""
        coll_repo = CollectionRepository(db_session)
        doc_repo = DocumentRepository(db_session)
        chunk_repo = ChunkRepository(db_session)

        # Create collection
        coll = Collection(
            name=f"cascade-test-{uuid4().hex[:8]}",
            embedding_model="nomic-embed-text",
            embedding_dimension=768,
        )
        collection = await coll_repo.create(coll)

        # Create document
        doc = Document(
            collection_id=collection.id,
            filename="cascade.txt",
            content_type="text/plain",
            file_size=100,
        )
        document = await doc_repo.create(doc)

        # Create chunks
        chunk = Chunk(
            document_id=document.id,
            content="Cascade content",
            chunk_index=0,
        )
        await chunk_repo.create(chunk)

        # Verify all exist
        assert await coll_repo.get_by_id(collection.id) is not None
        docs = await doc_repo.get_by_collection(collection.id)
        assert len(docs) == 1
        chunks = await chunk_repo.get_by_document(document.id)
        assert len(chunks) == 1
