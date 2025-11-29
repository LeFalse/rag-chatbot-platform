"""Factory for creating LLM providers."""

from typing import Literal

from app.core.config import get_settings
from app.providers.llm.base import BaseLLMProvider
from app.providers.llm.ollama import OllamaProvider
from app.providers.llm.openai import OpenAIProvider
from app.providers.llm.types import LLMConfig

ProviderType = Literal["openai", "ollama"]


def create_llm_provider(
    provider_type: ProviderType | None = None,
    *,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> BaseLLMProvider:
    """Create an LLM provider based on configuration.

    Factory pattern implementation for creating the appropriate
    LLM provider based on settings or explicit type.

    Args:
        provider_type: Provider to use ("openai" or "ollama").
                      Defaults to settings.llm_provider.
        model: Model name override.
        temperature: Temperature setting (0.0-2.0).
        max_tokens: Maximum tokens to generate.

    Returns:
        Configured LLM provider instance.

    Raises:
        ValueError: If provider type is invalid or OpenAI key is missing.

    Example:
        ```python
        # Use default provider from settings
        provider = create_llm_provider()

        # Use specific provider
        provider = create_llm_provider("ollama", model="llama3.2")

        # Generate response
        response = await provider.generate([
            {"role": "user", "content": "Hello!"}
        ])
        ```
    """
    settings = get_settings()
    provider = provider_type or settings.llm_provider

    config = LLMConfig(
        model=model or _get_default_model(provider, settings),
        temperature=temperature,
        max_tokens=max_tokens,
    )

    if provider == "ollama":
        return OllamaProvider(
            config=config,
            base_url=settings.ollama_base_url,
        )

    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable."
            )
        return OpenAIProvider(
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
        return getattr(settings, "ollama_model", "llama3.2")
    if provider == "openai":
        return getattr(settings, "openai_model", "gpt-4o-mini")
    return "unknown"


def get_available_providers() -> list[ProviderType]:
    """Get list of available providers based on configuration.

    Returns:
        List of provider types that can be used.
    """
    settings = get_settings()
    providers: list[ProviderType] = ["ollama"]  # Always available

    if settings.openai_api_key:
        providers.append("openai")

    return providers
