"""Exceptions for embedding providers."""


class EmbeddingProviderError(Exception):
    """Base exception for embedding provider errors."""

    def __init__(
        self,
        message: str,
        provider: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.retryable = retryable


class EmbeddingConnectionError(EmbeddingProviderError):
    """Raised when connection to embedding provider fails."""

    def __init__(self, provider: str, message: str = "Connection failed"):
        super().__init__(message, provider, retryable=True)


class EmbeddingRateLimitError(EmbeddingProviderError):
    """Raised when rate limit is exceeded."""

    def __init__(self, provider: str, retry_after: int | None = None):
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after}s" if retry_after else "Rate limit exceeded",
            provider,
            status_code=429,
            retryable=True,
        )
        self.retry_after = retry_after


class EmbeddingAuthenticationError(EmbeddingProviderError):
    """Raised when authentication fails."""

    def __init__(self, provider: str):
        super().__init__(
            "Authentication failed. Check API key.",
            provider,
            status_code=401,
            retryable=False,
        )


class EmbeddingInvalidRequestError(EmbeddingProviderError):
    """Raised when request is invalid."""

    def __init__(self, provider: str, message: str):
        super().__init__(message, provider, status_code=400, retryable=False)
