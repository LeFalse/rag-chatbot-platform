"""Ollama embedding provider implementation."""

import httpx

from app.providers.embedding.base import BaseEmbeddingProvider
from app.providers.embedding.exceptions import (
    EmbeddingConnectionError,
    EmbeddingInvalidRequestError,
    EmbeddingProviderError,
)
from app.providers.embedding.types import (
    BatchEmbeddingResult,
    EmbeddingConfig,
    EmbeddingResult,
)


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Ollama embedding provider for local inference.

    Uses the Ollama API for text embeddings.
    Default model: nomic-embed-text (768 dimensions).
    """

    def __init__(
        self,
        config: EmbeddingConfig,
        base_url: str = "http://localhost:11434",
        timeout: float = 60.0,
    ):
        """Initialize Ollama embedding provider.

        Args:
            config: Embedding configuration.
            base_url: Ollama API base URL.
            timeout: Request timeout in seconds.
        """
        super().__init__(config)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def embed(self, text: str) -> EmbeddingResult:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            EmbeddingResult with vector and metadata.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.config.model,
                        "prompt": text,
                    },
                )
                response.raise_for_status()
                data = response.json()

                return EmbeddingResult(
                    embedding=data["embedding"],
                    model=self.config.model,
                    tokens_used=len(text.split()),  # Approximate
                )

            except httpx.ConnectError as e:
                raise EmbeddingConnectionError(self.provider_name, str(e)) from e
            except httpx.HTTPStatusError as e:
                self._handle_http_error(e)
            except httpx.TimeoutException as e:
                raise EmbeddingConnectionError(
                    self.provider_name,
                    f"Request timed out after {self.timeout}s",
                ) from e

    async def embed_batch(self, texts: list[str]) -> BatchEmbeddingResult:
        """Generate embeddings for multiple texts.

        Note: Ollama doesn't have native batch support,
        so we process sequentially.

        Args:
            texts: List of texts to embed.

        Returns:
            BatchEmbeddingResult with vectors and metadata.
        """
        embeddings: list[list[float]] = []
        total_tokens = 0

        for text in texts:
            result = await self.embed(text)
            embeddings.append(result.embedding)
            total_tokens += result.tokens_used

        return BatchEmbeddingResult(
            embeddings=embeddings,
            model=self.config.model,
            total_tokens=total_tokens,
        )

    async def health_check(self) -> bool:
        """Check if Ollama is available.

        Returns:
            True if Ollama is responding.
        """
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
            except httpx.HTTPError:
                return False

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> None:
        """Handle HTTP errors from Ollama.

        Args:
            error: The HTTP error.

        Raises:
            EmbeddingProviderError: Appropriate exception for the error.
        """
        status = error.response.status_code

        try:
            detail = error.response.json().get("error", str(error))
        except Exception:
            detail = str(error)

        if status == 404:
            raise EmbeddingInvalidRequestError(
                self.provider_name,
                f"Model not found: {self.config.model}. Run: ollama pull {self.config.model}",
            )

        raise EmbeddingProviderError(
            detail,
            self.provider_name,
            status_code=status,
            retryable=status >= 500,
        )
