"""Embedding providers module."""

from app.providers.embedding.base import BaseEmbeddingProvider
from app.providers.embedding.exceptions import (
    EmbeddingAuthenticationError,
    EmbeddingConnectionError,
    EmbeddingInvalidRequestError,
    EmbeddingProviderError,
    EmbeddingRateLimitError,
)
from app.providers.embedding.factory import (
    EmbeddingProviderType,
    create_embedding_provider,
    get_available_embedding_providers,
)
from app.providers.embedding.ollama import OllamaEmbeddingProvider
from app.providers.embedding.openai import OpenAIEmbeddingProvider
from app.providers.embedding.types import (
    BatchEmbeddingResult,
    EmbeddingConfig,
    EmbeddingResult,
)

__all__ = [
    # Base
    "BaseEmbeddingProvider",
    # Providers
    "OllamaEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    # Factory
    "create_embedding_provider",
    "get_available_embedding_providers",
    "EmbeddingProviderType",
    # Types
    "EmbeddingConfig",
    "EmbeddingResult",
    "BatchEmbeddingResult",
    # Exceptions
    "EmbeddingProviderError",
    "EmbeddingConnectionError",
    "EmbeddingRateLimitError",
    "EmbeddingAuthenticationError",
    "EmbeddingInvalidRequestError",
]
