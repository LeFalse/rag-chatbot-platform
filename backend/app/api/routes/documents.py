"""Document management routes."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.collection import Collection
from app.schemas.requests.schemas import (
    CreateCollectionRequest,
    UploadDocumentRequest,
)
from app.schemas.responses.schemas import DocumentResponse, CollectionResponse
from app.services.document_service import DocumentService
from app.repositories.document_repo import DocumentRepository
from app.repositories.collection_repo import CollectionRepository

router = APIRouter(prefix="/documents", tags=["documents"])


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
            embedding_model=collection.embedding_model,
            embedding_dimension=collection.embedding_dimension,
            document_count=0,
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
                embedding_model=c.embedding_model,
                embedding_dimension=c.embedding_dimension,
                document_count=len(c.documents),
                created_at=c.created_at,
            )
            for c in collections
        ]
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
        return DocumentResponse(
            id=str(doc.id),
            filename=doc.filename,
            collection_id=str(doc.collection_id),
            chunk_count=0,
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
        docs = await repo.get_by_collection(collection_uuid)
        return [
            DocumentResponse(
                id=str(doc.id),
                filename=doc.filename,
                collection_id=str(doc.collection_id),
                chunk_count=0,
                created_at=doc.created_at,
            )
            for doc in docs
        ]
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
