"""Base interface for embedding providers."""

from abc import ABC, abstractmethod

from app.providers.embedding.types import (
    BatchEmbeddingResult,
    EmbeddingConfig,
    EmbeddingResult,
)


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers.

    Implements the Strategy pattern - any provider can be swapped
    without changing the calling code.
    """

    def __init__(self, config: EmbeddingConfig):
        """Initialize provider with configuration.

        Args:
            config: Embedding configuration settings.
        """
        self.config = config

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider."""
        ...

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self.config.dimension

    @abstractmethod
    async def embed(self, text: str) -> EmbeddingResult:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            EmbeddingResult with vector and metadata.

        Raises:
            EmbeddingProviderError: If the API call fails.
        """
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> BatchEmbeddingResult:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.

        Returns:
            BatchEmbeddingResult with vectors and metadata.

        Raises:
            EmbeddingProviderError: If the API call fails.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available.

        Returns:
            True if provider is healthy, False otherwise.
        """
        ...
