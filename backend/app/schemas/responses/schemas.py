"""Response schemas for API endpoints."""

from datetime import datetime
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """Response for a document."""
    id: str = Field(..., description="Document ID")
    filename: str = Field(..., description="Document filename")
    collection_id: str = Field(..., description="Collection ID")
    chunk_count: int = Field(..., description="Number of chunks")
    status: str = Field("pending", description="Processing status: pending, processing, completed, failed")
    error: str | None = Field(None, description="Error message if processing failed")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Response for a conversation."""
    id: str = Field(..., description="Conversation ID")
    collection_id: str = Field(..., description="Collection ID")
    title: str = Field(..., description="Conversation title")
    message_count: int = Field(0, description="Number of messages")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Response for a message."""
    id: str = Field(..., description="Message ID")
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    created_at: datetime = Field(..., description="Creation timestamp")
    latency_ms: int | None = Field(None, description="Response latency in ms")
    model: str | None = Field(None, description="LLM model used")

    class Config:
        from_attributes = True


class ConversationHistoryResponse(BaseModel):
    """Response for conversation history."""
    conversation_id: str = Field(..., description="Conversation ID")
    messages: list[MessageResponse] = Field(..., description="List of messages")


class MetricsResponse(BaseModel):
    """Response for metrics."""
    date: str = Field(..., description="Metrics date")
    metric_type: str = Field(..., description="Type of metric")
    provider_name: str = Field(..., description="Provider name")
    count: int = Field(..., description="Count of operations")
    total_latency_ms: int = Field(..., description="Total latency in ms")
    average_latency_ms: float = Field(..., description="Average latency in ms")


class MCPConfigResponse(BaseModel):
    """MCP configuration response."""

    gitlab: dict | None = Field(None, description="GitLab MCP configuration")


class CollectionResponse(BaseModel):
    """Response for a collection."""

    id: str = Field(..., description="Collection ID")
    name: str = Field(..., description="Collection name")
    description: str | None = Field(None, description="Collection description")
    embedding_model: str = Field(..., description="Embedding model")
    embedding_dimension: int = Field(..., description="Embedding dimension")
    document_count: int = Field(0, description="Number of documents")
    # Agent configuration
    system_prompt: str | None = Field(None, description="Custom system prompt")
    personality: str | None = Field("professional", description="Personality preset")
    temperature: float = Field(0.5, description="LLM temperature")
    max_tokens: int = Field(512, description="Max response tokens")
    top_k: int = Field(5, description="Number of chunks to retrieve")
    # MCP configuration
    mcp_config: MCPConfigResponse | None = Field(None, description="MCP tool configuration")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class StreamingResponse(BaseModel):
    """Response for streaming answer."""
    content: str = Field(..., description="Response chunk")
    finish_reason: str | None = Field(None, description="Finish reason (stop/etc)")


class ErrorResponse(BaseModel):
    """Response for errors."""
    detail: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
