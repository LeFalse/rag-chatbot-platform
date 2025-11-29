"""Document service - handles upload, chunking, and storage."""

import hashlib
import os
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk as ChunkModel
from app.models.document import Document as DocumentModel
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.collection_repo import CollectionRepository
from app.repositories.document_repo import DocumentRepository
from app.services.document_processor import (
    DocumentProcessor,
    FixedSizeChunking,
    MarkdownExtractor,
    PlainTextExtractor,
)


class DocumentService:
    """Service for managing document uploads, extraction, and chunking."""

    UPLOAD_DIR = Path("uploads")
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.chunk_repo = ChunkRepository(session)
        self.collection_repo = CollectionRepository(session)
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    async def upload_document(
        self,
        collection_id: UUID,
        file_content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> DocumentModel:
        """Upload and save a document to the collection.

        Args:
            collection_id: Collection to add document to.
            file_content: Binary file content.
            filename: Original filename.
            content_type: MIME type of the file.

        Returns:
            Created Document model.

        Raises:
            ValueError: If file is too large or collection doesn't exist.
        """
        # Validate collection exists
        collection = await self.collection_repo.get(collection_id)
        if not collection:
            raise ValueError(f"Collection {collection_id} not found")

        # Validate file size
        if len(file_content) > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File size exceeds maximum {self.MAX_FILE_SIZE} bytes"
            )

        # Check for duplicate filename in collection
        existing = await self.doc_repo.get_by_filename(collection_id, filename)
        if existing:
            raise ValueError(f"Document '{filename}' already exists in collection")

        # Save file to disk
        file_path = self.UPLOAD_DIR / str(collection_id) / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(file_content)

        # Create document record
        document = DocumentModel(
            collection_id=collection_id,
            filename=filename,
            content_type=content_type,
            file_size=len(file_content),
            metadata_={
                "source": "upload",
                "original_filename": filename,
                "mime_type": content_type,
            },
        )

        self.session.add(document)
        await self.session.flush()

        return document

    async def process_and_chunk(
        self,
        document_id: UUID,
        chunk_size: int = 512,
        overlap: int = 50,
    ) -> list[ChunkModel]:
        """Extract text from document and create chunks.

        Args:
            document_id: Document to process.
            chunk_size: Characters per chunk.
            overlap: Overlapping characters between chunks.

        Returns:
            List of created Chunk models.

        Raises:
            ValueError: If document not found or extraction fails.
        """
        # Get document
        document = await self.doc_repo.get(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Get file path
        file_path = (
            self.UPLOAD_DIR
            / str(document.collection_id)
            / document.filename
        )

        if not file_path.exists():
            raise ValueError(f"Document file not found: {file_path}")

        # Determine extractor based on file extension
        ext = Path(document.filename).suffix.lower()
        if ext == ".md":
            extractor = MarkdownExtractor()
        else:
            extractor = PlainTextExtractor()

        # Create processor and process document
        chunking_strategy = FixedSizeChunking()
        processor = DocumentProcessor(extractor, chunking_strategy)

        chunks = await processor.process(
            str(file_path),
            chunk_size=chunk_size,
            overlap=overlap,
        )

        # Create chunk models
        chunk_models: list[ChunkModel] = []
        for idx, chunk in enumerate(chunks):
            chunk_model = ChunkModel(
                document_id=document_id,
                content=chunk.content,
                chunk_index=idx,
                metadata_={
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "page": chunk.page,
                    "section": chunk.section,
                },
            )
            chunk_models.append(chunk_model)

        # Bulk create chunks
        created_chunks = await self.chunk_repo.bulk_create(chunk_models)

        return created_chunks

    async def delete_document(self, document_id: UUID) -> None:
        """Delete a document and all its chunks.

        Args:
            document_id: Document to delete.

        Raises:
            ValueError: If document not found.
        """
        document = await self.doc_repo.get(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Delete chunks first (via cascade in DB)
        await self.chunk_repo.delete_by_document(document_id)

        # Delete document
        await self.doc_repo.delete(document_id)

        # Delete file from disk
        file_path = (
            self.UPLOAD_DIR
            / str(document.collection_id)
            / document.filename
        )
        if file_path.exists():
            file_path.unlink()

    async def get_document_stats(self, document_id: UUID) -> dict:
        """Get statistics about a document.

        Args:
            document_id: Document to get stats for.

        Returns:
            Dictionary with document statistics.

        Raises:
            ValueError: If document not found.
        """
        document = await self.doc_repo.get_with_chunks(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        chunks = document.chunks
        total_chars = sum(len(chunk.content) for chunk in chunks)
        avg_chunk_size = (
            total_chars / len(chunks) if chunks else 0
        )

        return {
            "document_id": str(document_id),
            "filename": document.filename,
            "file_size": document.file_size,
            "chunk_count": len(chunks),
            "total_content_chars": total_chars,
            "avg_chunk_size": avg_chunk_size,
            "created_at": document.created_at.isoformat(),
        }
