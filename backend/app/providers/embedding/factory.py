"""Factory for creating embedding providers."""

from typing import Literal

from app.core.config import get_settings
from app.providers.embedding.base import BaseEmbeddingProvider
from app.providers.embedding.ollama import OllamaEmbeddingProvider
from app.providers.embedding.openai import OpenAIEmbeddingProvider
from app.providers.embedding.types import EmbeddingConfig

EmbeddingProviderType = Literal["openai", "ollama"]


def create_embedding_provider(
    provider_type: EmbeddingProviderType | None = None,
    *,
    model: str | None = None,
    dimension: int | None = None,
) -> BaseEmbeddingProvider:
    """Create an embedding provider based on configuration.

    Factory pattern implementation for creating the appropriate
    embedding provider based on settings or explicit type.

    Args:
        provider_type: Provider to use ("openai" or "ollama").
                      Defaults to settings.embedding_provider.
        model: Model name override.
        dimension: Embedding dimension override.

    Returns:
        Configured embedding provider instance.

    Raises:
        ValueError: If provider type is invalid or OpenAI key is missing.

    Example:
        ```python
        # Use default provider from settings
        provider = create_embedding_provider()

        # Use specific provider
        provider = create_embedding_provider("ollama", model="nomic-embed-text")

        # Generate embedding
        result = await provider.embed("Hello world")
        print(len(result.embedding))  # 768 for nomic-embed-text
        ```
    """
    settings = get_settings()
    provider = provider_type or settings.embedding_provider

    config = EmbeddingConfig(
        model=model or _get_default_model(provider, settings),
        dimension=dimension or _get_default_dimension(provider, settings),
    )

    if provider == "ollama":
        return OllamaEmbeddingProvider(
            config=config,
            base_url=settings.ollama_base_url,
        )

    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable."
            )
        return OpenAIEmbeddingProvider(
            config=config,
            api_key=settings.openai_api_key,
        )

    raise ValueError(f"Unknown provider type: {provider}")


def _get_default_model(provider: str, settings: object) -> str:
    """Get the default model for a provider.

    Args:
        provider: Provider type.
        settings: Application settings.

    Returns:
        Default model name for the provider.
    """
    if provider == "ollama":
        return getattr(settings, "embedding_model", "nomic-embed-text")
    if provider == "openai":
        return getattr(settings, "openai_embedding_model", "text-embedding-3-small")
    return "unknown"


def _get_default_dimension(provider: str, settings: object) -> int:
    """Get the default embedding dimension for a provider.

    Args:
        provider: Provider type.
        settings: Application settings.

    Returns:
        Default embedding dimension.
    """
    if provider == "ollama":
        return getattr(settings, "embedding_dimension", 768)
    if provider == "openai":
        return 1536  # text-embedding-3-small default
    return 768


def get_available_embedding_providers() -> list[EmbeddingProviderType]:
    """Get list of available embedding providers based on configuration.

    Returns:
        List of provider types that can be used.
    """
    settings = get_settings()
    providers: list[EmbeddingProviderType] = ["ollama"]

    if settings.openai_api_key:
        providers.append("openai")

    return providers
