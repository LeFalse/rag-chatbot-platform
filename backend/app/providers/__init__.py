"""Providers module - external service abstractions."""

from app.providers.embedding import (
    BaseEmbeddingProvider,
    BatchEmbeddingResult,
    EmbeddingConfig,
    EmbeddingProviderError,
    EmbeddingProviderType,
    EmbeddingResult,
    OllamaEmbeddingProvider,
    OpenAIEmbeddingProvider,
    create_embedding_provider,
    get_available_embedding_providers,
)
from app.providers.llm import (
    BaseLLMProvider,
    ChatMessage,
    LLMConfig,
    LLMProviderError,
    LLMResponse,
    OllamaProvider,
    OpenAIProvider,
    ProviderType,
    StreamChunk,
    create_llm_provider,
    get_available_providers,
)

__all__ = [
    # LLM
    "BaseLLMProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "create_llm_provider",
    "get_available_providers",
    "ProviderType",
    "ChatMessage",
    "LLMConfig",
    "LLMResponse",
    "StreamChunk",
    "LLMProviderError",
    # Embedding
    "BaseEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "create_embedding_provider",
    "get_available_embedding_providers",
    "EmbeddingProviderType",
    "EmbeddingConfig",
    "EmbeddingResult",
    "BatchEmbeddingResult",
    "EmbeddingProviderError",
]
