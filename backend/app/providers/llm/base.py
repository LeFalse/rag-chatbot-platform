"""Base interface for LLM providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.providers.llm.types import ChatMessage, LLMConfig, LLMResponse, StreamChunk


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers.

    Implements the Strategy pattern - any provider can be swapped
    without changing the calling code.
    """

    def __init__(self, config: LLMConfig):
        """Initialize provider with configuration.

        Args:
            config: LLM configuration settings.
        """
        self.config = config

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider."""
        ...

    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a complete response from the LLM.

        Args:
            messages: List of chat messages (conversation history).
            temperature: Override default temperature (0.0-2.0).
            max_tokens: Override default max tokens.

        Returns:
            LLMResponse with content and token usage.

        Raises:
            LLMProviderError: If the API call fails.
        """
        ...

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response from the LLM.

        Args:
            messages: List of chat messages.
            temperature: Override default temperature.
            max_tokens: Override default max tokens.

        Yields:
            StreamChunk with partial content.

        Raises:
            LLMProviderError: If the API call fails.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available.

        Returns:
            True if provider is healthy, False otherwise.
        """
        ...
