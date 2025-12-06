"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "RAG Chatbot Platform"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://raguser:ragpass@localhost:5432/ragdb"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM Providers
    llm_provider: Literal["openai", "ollama"] = "ollama"
    openai_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # Embedding
    embedding_provider: Literal["openai", "ollama"] = "ollama"
    embedding_model: str = "nomic-embed-text"
    embedding_dimension: int = 768

    # OpenAI specific
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Ollama specific
    # LLM_MODEL env var is shared with docker-compose for Ollama container
    ollama_model: str = "qwen3:8b"
    llm_model: str = "qwen3:8b"  # Alias for frontend display

    # LLM Generation limits
    max_tokens_default: int = 512  # Default for new collections
    max_tokens_limit: int = 8192  # Maximum allowed value

    # Document processing
    chunk_size: int = 512
    chunk_overlap: int = 50

    # Rate limiting
    rate_limit_chat: int = 60  # requests per minute
    rate_limit_default: int = 100


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
