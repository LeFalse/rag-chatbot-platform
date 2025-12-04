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
    similarity_threshold: float = Field(0.5, description="Minimum similarity score")
    llm_provider: str = Field("ollama", description="LLM provider to use: 'ollama' or 'openai'")


class CreateCollectionRequest(BaseModel):
    """Request for creating a collection."""
    name: str = Field(..., description="Collection name")
    embedding_model: str = Field(..., description="Embedding model name")
    embedding_dimension: int = Field(..., description="Embedding dimension")


class UpdateCollectionRequest(BaseModel):
    """Request for updating a collection's configuration."""
    name: str | None = Field(None, description="Collection name")
    description: str | None = Field(None, description="Collection description")
    system_prompt: str | None = Field(None, description="Custom system prompt")
    personality: str | None = Field(
        None, description="Personality preset: professional, friendly, technical, custom"
    )
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="LLM temperature")
    max_tokens: int | None = Field(None, ge=1, le=4096, description="Max response tokens")
    top_k: int | None = Field(None, ge=1, le=20, description="Number of chunks to retrieve")
