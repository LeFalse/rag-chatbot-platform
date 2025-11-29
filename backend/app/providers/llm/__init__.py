"""LLM providers module."""

from app.providers.llm.base import BaseLLMProvider
from app.providers.llm.exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMInvalidRequestError,
    LLMProviderError,
    LLMRateLimitError,
)
from app.providers.llm.factory import (
    ProviderType,
    create_llm_provider,
    get_available_providers,
)
from app.providers.llm.ollama import OllamaProvider
from app.providers.llm.openai import OpenAIProvider
from app.providers.llm.types import ChatMessage, LLMConfig, LLMResponse, StreamChunk

__all__ = [
    # Base
    "BaseLLMProvider",
    # Providers
    "OllamaProvider",
    "OpenAIProvider",
    # Factory
    "create_llm_provider",
    "get_available_providers",
    "ProviderType",
    # Types
    "ChatMessage",
    "LLMConfig",
    "LLMResponse",
    "StreamChunk",
    # Exceptions
    "LLMProviderError",
    "LLMConnectionError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
    "LLMInvalidRequestError",
]
