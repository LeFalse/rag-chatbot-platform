"""Document management routes."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.collection import Collection
from app.models.document import Document
from app.schemas.requests.schemas import (
    CreateCollectionRequest,
    UpdateCollectionRequest,
    UploadDocumentRequest,
)
from app.schemas.responses.schemas import DocumentResponse, CollectionResponse
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.cache.embedding_cache import EmbeddingCache
from app.services.cache.redis_client import get_redis_client
from app.repositories.document_repo import DocumentRepository
from app.repositories.collection_repo import CollectionRepository
from app.providers.embedding.factory import create_embedding_provider

router = APIRouter(prefix="/documents", tags=["documents"])


def get_doc_status(doc: Document) -> tuple[str, str | None]:
    """Get processing status and error from document metadata."""
    metadata = doc.metadata_ or {}
    status = metadata.get("processing_status", "pending")
    error = metadata.get("processing_error")

    # If document has chunks and status is not failed, it's completed
    if hasattr(doc, "chunks") and len(doc.chunks) > 0 and status != "failed":
        status = "completed"

    return status, error


@router.post("/collections")
async def create_collection(
    request: CreateCollectionRequest,
    session: AsyncSession = Depends(get_session),
):
    """Create a new collection."""
    try:
        repo = CollectionRepository(session)
        collection_obj = Collection(
            name=request.name,
            embedding_model=request.embedding_model,
            embedding_dimension=request.embedding_dimension,
        )
        collection = await repo.create(collection_obj)
        return CollectionResponse(
            id=str(collection.id),
            name=collection.name,
            description=collection.description,
            embedding_model=collection.embedding_model,
            embedding_dimension=collection.embedding_dimension,
            document_count=0,
            system_prompt=collection.system_prompt,
            personality=collection.personality,
            temperature=collection.temperature,
            max_tokens=collection.max_tokens,
            top_k=collection.top_k,
            created_at=collection.created_at,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collections")
async def list_collections(
    session: AsyncSession = Depends(get_session),
):
    """List all collections."""
    try:
        repo = CollectionRepository(session)
        collections = await repo.get_all_with_documents()
        return [
            CollectionResponse(
                id=str(c.id),
                name=c.name,
                description=c.description,
                embedding_model=c.embedding_model,
                embedding_dimension=c.embedding_dimension,
                document_count=len(c.documents),
                system_prompt=c.system_prompt,
                personality=c.personality,
                temperature=c.temperature,
                max_tokens=c.max_tokens,
                top_k=c.top_k,
                created_at=c.created_at,
            )
            for c in collections
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collections/{collection_id}")
async def delete_collection(
    collection_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a collection and all its documents."""
    try:
        collection_uuid = UUID(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID format")

    try:
        collection_repo = CollectionRepository(session)
        collection = await collection_repo.get_by_id(collection_uuid)
        if not collection:
            return {"message": "Collection deleted successfully"}  # Idempotent

        # Delete all documents (this will delete files too)
        service = DocumentService(session)
        doc_repo = DocumentRepository(session)
        docs = await doc_repo.get_by_collection(collection_uuid)
        for doc in docs:
            await service.delete_document(doc.id)

        # Delete collection
        await collection_repo.delete(collection_uuid)

        # Delete collection folder from uploads
        import asyncio
        from pathlib import Path
        folder_path = Path("uploads") / str(collection_uuid)
        if await asyncio.to_thread(folder_path.exists):
            import shutil
            await asyncio.to_thread(shutil.rmtree, folder_path)

        return {"message": "Collection deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/collections/{collection_id}")
async def update_collection(
    collection_id: str,
    request: UpdateCollectionRequest,
    session: AsyncSession = Depends(get_session),
):
    """Update a collection's configuration."""
    try:
        collection_uuid = UUID(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID format")

    try:
        repo = CollectionRepository(session)
        # Use get_with_documents to eagerly load documents for count
        collection = await repo.get_with_documents(collection_uuid)
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        # Update only provided fields
        if request.name is not None:
            collection.name = request.name
        if request.description is not None:
            collection.description = request.description
        if request.system_prompt is not None:
            collection.system_prompt = request.system_prompt
        if request.personality is not None:
            collection.personality = request.personality
        if request.temperature is not None:
            collection.temperature = request.temperature
        if request.max_tokens is not None:
            collection.max_tokens = request.max_tokens
        if request.top_k is not None:
            collection.top_k = request.top_k

        await session.flush()

        return CollectionResponse(
            id=str(collection.id),
            name=collection.name,
            description=collection.description,
            embedding_model=collection.embedding_model,
            embedding_dimension=collection.embedding_dimension,
            document_count=len(collection.documents) if collection.documents else 0,
            system_prompt=collection.system_prompt,
            personality=collection.personality,
            temperature=collection.temperature,
            max_tokens=collection.max_tokens,
            top_k=collection.top_k,
            created_at=collection.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{collection_id}/upload")
async def upload_document(
    collection_id: str,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """Upload a document."""
    try:
        collection_uuid = UUID(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID format")

    try:
        service = DocumentService(session)
        doc = await service.upload_document(
            collection_uuid,
            await file.read(),
            file.filename,
            file.content_type,
        )

        # Set initial processing status
        doc.metadata_ = {**doc.metadata_, "processing_status": "pending"}
        await session.flush()

        return DocumentResponse(
            id=str(doc.id),
            filename=doc.filename,
            collection_id=str(doc.collection_id),
            chunk_count=0,
            status="pending",
            error=None,
            created_at=doc.created_at,
        )
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{collection_id}")
async def list_documents(
    collection_id: str,
    session: AsyncSession = Depends(get_session),
):
    """List documents in a collection."""
    try:
        collection_uuid = UUID(collection_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid collection ID format")

    try:
        repo = DocumentRepository(session)
        docs = await repo.get_by_collection_with_chunks(collection_uuid)
        result = []
        for doc in docs:
            status, error = get_doc_status(doc)
            result.append(
                DocumentResponse(
                    id=str(doc.id),
                    filename=doc.filename,
                    collection_id=str(doc.collection_id),
                    chunk_count=len(doc.chunks),
                    status=status,
                    error=error,
                    created_at=doc.created_at,
                )
            )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a document (idempotent)."""
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")

    try:
        service = DocumentService(session)
        doc = await service.doc_repo.get_by_id(doc_uuid)
        if doc:
            await service.delete_document(doc_uuid)
        return {"message": "Document deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/content")
async def get_document_content(
    document_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get the text content of a document for preview.

    Returns the raw text content of the uploaded document file.
    """
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")

    try:
        repo = DocumentRepository(session)
        doc = await repo.get_by_id(doc_uuid)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Read file from disk
        from pathlib import Path
        import asyncio

        file_path = Path("uploads") / str(doc.collection_id) / doc.filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Document file not found")

        content = await asyncio.to_thread(file_path.read_text, encoding="utf-8")

        return {
            "document_id": document_id,
            "filename": doc.filename,
            "content": content,
            "content_type": doc.content_type,
        }
    except HTTPException:
        raise
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Cannot read document content - file may be binary"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{document_id}/process")
async def process_document(
    document_id: str,
    chunk_size: int = 512,
    overlap: int = 50,
    session: AsyncSession = Depends(get_session),
):
    """Process document: extract text, create chunks, and generate embeddings.

    This endpoint performs the full RAG ingestion pipeline:
    1. Extract text from the document
    2. Split into chunks with overlap
    3. Generate embeddings for each chunk
    4. Store embeddings in pgvector

    Args:
        document_id: Document UUID to process.
        chunk_size: Characters per chunk (default 512).
        overlap: Overlapping characters between chunks (default 50).

    Returns:
        Processing statistics including chunk count and embeddings generated.
    """
    try:
        doc_uuid = UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID format")

    doc_repo = DocumentRepository(session)
    doc = await doc_repo.get_by_id(doc_uuid)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        # Update status to processing
        doc.metadata_ = {**doc.metadata_, "processing_status": "processing", "processing_error": None}
        await session.flush()

        # Step 1 & 2: Extract text and create chunks
        doc_service = DocumentService(session)
        chunks = await doc_service.process_and_chunk(
            doc_uuid,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        if not chunks:
            # Update status to failed
            doc.metadata_ = {**doc.metadata_, "processing_status": "failed", "processing_error": "No chunks created - document may be empty"}
            await session.commit()
            return {
                "document_id": document_id,
                "chunk_count": 0,
                "embeddings_generated": 0,
                "status": "failed",
                "message": "No chunks created - document may be empty",
            }

        # Step 3 & 4: Generate embeddings and store in pgvector
        embedding_provider = create_embedding_provider()
        redis_client = await get_redis_client()
        embedding_cache = EmbeddingCache(redis_client)
        embedding_service = EmbeddingService(
            session,
            embedding_provider,
            embedding_cache,
        )

        embeddings_count = await embedding_service.embed_chunks(doc_uuid)

        # Update status to completed
        doc.metadata_ = {**doc.metadata_, "processing_status": "completed", "processing_error": None}
        await session.commit()

        return {
            "document_id": document_id,
            "chunk_count": len(chunks),
            "embeddings_generated": embeddings_count,
            "status": "completed",
            "message": "Document processed successfully",
        }

    except ValueError as e:
        error_msg = str(e)
        # Update status to failed
        doc.metadata_ = {**doc.metadata_, "processing_status": "failed", "processing_error": error_msg}
        await session.commit()
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        error_msg = str(e)
        # Update status to failed
        doc.metadata_ = {**doc.metadata_, "processing_status": "failed", "processing_error": error_msg}
        await session.commit()
        raise HTTPException(status_code=500, detail=error_msg)
