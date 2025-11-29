"""OpenAI embedding provider implementation."""

from openai import (
    APIConnectionError,
    APIStatusError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from app.providers.embedding.base import BaseEmbeddingProvider
from app.providers.embedding.exceptions import (
    EmbeddingAuthenticationError,
    EmbeddingConnectionError,
    EmbeddingInvalidRequestError,
    EmbeddingProviderError,
    EmbeddingRateLimitError,
)
from app.providers.embedding.types import (
    BatchEmbeddingResult,
    EmbeddingConfig,
    EmbeddingResult,
)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider.

    Uses the official OpenAI Python SDK for embeddings.
    Default model: text-embedding-3-small (1536 dimensions).
    """

    def __init__(
        self,
        config: EmbeddingConfig,
        api_key: str,
        timeout: float = 60.0,
    ):
        """Initialize OpenAI embedding provider.

        Args:
            config: Embedding configuration.
            api_key: OpenAI API key.
            timeout: Request timeout in seconds.
        """
        super().__init__(config)
        self.client = AsyncOpenAI(api_key=api_key, timeout=timeout)

    @property
    def provider_name(self) -> str:
        return "openai"

    async def embed(self, text: str) -> EmbeddingResult:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            EmbeddingResult with vector and metadata.
        """
        try:
            response = await self.client.embeddings.create(
                model=self.config.model,
                input=text,
            )

            return EmbeddingResult(
                embedding=response.data[0].embedding,
                model=response.model,
                tokens_used=response.usage.total_tokens,
            )

        except AuthenticationError as e:
            raise EmbeddingAuthenticationError(self.provider_name) from e
        except RateLimitError as e:
            raise EmbeddingRateLimitError(self.provider_name) from e
        except APIConnectionError as e:
            raise EmbeddingConnectionError(self.provider_name, str(e)) from e
        except APIStatusError as e:
            self._handle_api_error(e)

    async def embed_batch(self, texts: list[str]) -> BatchEmbeddingResult:
        """Generate embeddings for multiple texts.

        OpenAI supports native batch embedding.

        Args:
            texts: List of texts to embed.

        Returns:
            BatchEmbeddingResult with vectors and metadata.
        """
        try:
            response = await self.client.embeddings.create(
                model=self.config.model,
                input=texts,
            )

            # Sort by index to ensure correct order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            embeddings = [item.embedding for item in sorted_data]

            return BatchEmbeddingResult(
                embeddings=embeddings,
                model=response.model,
                total_tokens=response.usage.total_tokens,
            )

        except AuthenticationError as e:
            raise EmbeddingAuthenticationError(self.provider_name) from e
        except RateLimitError as e:
            raise EmbeddingRateLimitError(self.provider_name) from e
        except APIConnectionError as e:
            raise EmbeddingConnectionError(self.provider_name, str(e)) from e
        except APIStatusError as e:
            self._handle_api_error(e)

    async def health_check(self) -> bool:
        """Check if OpenAI API is available.

        Returns:
            True if API is responding with valid credentials.
        """
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False

    def _handle_api_error(self, error: APIStatusError) -> None:
        """Handle API errors from OpenAI.

        Args:
            error: The API error.

        Raises:
            EmbeddingProviderError: Appropriate exception for the error.
        """
        status = error.status_code
        message = str(error.message) if hasattr(error, "message") else str(error)

        if status == 400:
            raise EmbeddingInvalidRequestError(self.provider_name, message)

        raise EmbeddingProviderError(
            message,
            self.provider_name,
            status_code=status,
            retryable=status >= 500,
        )
