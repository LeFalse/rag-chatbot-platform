"""Request schemas for API endpoints."""

from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings


class GitLabMCPConfig(BaseModel):
    """GitLab MCP configuration."""

    enabled: bool = Field(True, description="Whether GitLab MCP is enabled")
    project_id: str = Field(..., description="GitLab project ID (e.g., 'group/project')")
    gitlab_url: str = Field(
        "https://gitlab.com", description="GitLab instance URL"
    )


class MCPConfigRequest(BaseModel):
    """MCP configuration for a collection."""

    gitlab: GitLabMCPConfig | None = Field(None, description="GitLab MCP configuration")


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
    max_tokens: int | None = Field(None, ge=1, description="Max response tokens")
    top_k: int | None = Field(None, ge=1, le=20, description="Number of chunks to retrieve")
    mcp_config: MCPConfigRequest | None = Field(None, description="MCP tool configuration")

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int | None) -> int | None:
        """Validate max_tokens against configured limit."""
        if v is not None:
            settings = get_settings()
            if v > settings.max_tokens_limit:
                raise ValueError(
                    f"max_tokens must be at most {settings.max_tokens_limit}"
                )
        return v
