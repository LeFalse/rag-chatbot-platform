"""Request schemas for API endpoints."""

from pydantic import BaseModel, Field


class UploadDocumentRequest(BaseModel):
    """Request for uploading a document."""
    filename: str = Field(..., description="Document filename")
    collection_id: str = Field(..., description="Collection ID (UUID)")


class CreateConversationRequest(BaseModel):
    """Request for creating a conversation."""
    collection_id: str = Field(..., description="Collection ID (UUID)")
    title: str = Field(..., description="Conversation title")


class AskQuestionRequest(BaseModel):
    """Request for asking a question in a conversation."""
    question: str = Field(..., description="User's question")
    top_k: int = Field(5, description="Number of similar chunks to retrieve")
    similarity_threshold: float = Field(0.7, description="Minimum similarity score")


class CreateCollectionRequest(BaseModel):
    """Request for creating a collection."""
    name: str = Field(..., description="Collection name")
    embedding_model: str = Field(..., description="Embedding model name")
    embedding_dimension: int = Field(..., description="Embedding dimension")
