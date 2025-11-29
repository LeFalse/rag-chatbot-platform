"""Ollama LLM provider implementation."""

import json
from collections.abc import AsyncIterator

import httpx

from app.providers.llm.base import BaseLLMProvider
from app.providers.llm.exceptions import (
    LLMConnectionError,
    LLMInvalidRequestError,
    LLMProviderError,
)
from app.providers.llm.types import (
    ChatMessage,
    LLMConfig,
    LLMResponse,
    StreamChunk,
)


class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider for local inference.

    Uses the Ollama API for chat completions.
    Supports streaming responses.
    """

    def __init__(
        self,
        config: LLMConfig,
        base_url: str = "http://localhost:11434",
        timeout: float = 120.0,
    ):
        """Initialize Ollama provider.

        Args:
            config: LLM configuration.
            base_url: Ollama API base URL.
            timeout: Request timeout in seconds.
        """
        super().__init__(config)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a complete response from Ollama.

        Args:
            messages: Chat messages.
            temperature: Override temperature.
            max_tokens: Override max tokens.

        Returns:
            LLMResponse with content and metadata.
        """
        payload = self._build_payload(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                return LLMResponse(
                    content=data["message"]["content"],
                    model=data.get("model", self.config.model),
                    tokens_input=data.get("prompt_eval_count", 0),
                    tokens_output=data.get("eval_count", 0),
                    finish_reason=data.get("done_reason"),
                )

            except httpx.ConnectError as e:
                raise LLMConnectionError(self.provider_name, str(e)) from e
            except httpx.HTTPStatusError as e:
                self._handle_http_error(e)
            except httpx.TimeoutException as e:
                raise LLMConnectionError(
                    self.provider_name,
                    f"Request timed out after {self.timeout}s",
                ) from e

    async def generate_stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response from Ollama.

        Args:
            messages: Chat messages.
            temperature: Override temperature.
            max_tokens: Override max tokens.

        Yields:
            StreamChunk with partial content.
        """
        payload = self._build_payload(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        message = data.get("message", {})
                        content = message.get("content", "")
                        is_done = data.get("done", False)

                        if content or is_done:
                            yield StreamChunk(
                                content=content,
                                is_final=is_done,
                                finish_reason=data.get("done_reason"),
                            )

            except httpx.ConnectError as e:
                raise LLMConnectionError(self.provider_name, str(e)) from e
            except httpx.HTTPStatusError as e:
                self._handle_http_error(e)
            except httpx.TimeoutException as e:
                raise LLMConnectionError(
                    self.provider_name,
                    f"Request timed out after {self.timeout}s",
                ) from e

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

    def _build_payload(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None,
        max_tokens: int | None,
        stream: bool,
    ) -> dict[str, object]:
        """Build the API request payload.

        Args:
            messages: Chat messages.
            temperature: Temperature override.
            max_tokens: Max tokens override.
            stream: Whether to stream.

        Returns:
            Request payload dictionary.
        """
        return {
            "model": self.config.model,
            "messages": [dict(m) for m in messages],
            "stream": stream,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
                "top_p": self.config.top_p,
                "stop": self.config.stop_sequences or None,
            },
        }

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> None:
        """Handle HTTP errors from Ollama.

        Args:
            error: The HTTP error.

        Raises:
            LLMProviderError: Appropriate exception for the error.
        """
        status = error.response.status_code

        try:
            detail = error.response.json().get("error", str(error))
        except (json.JSONDecodeError, KeyError):
            detail = str(error)

        if status == 404:
            raise LLMInvalidRequestError(
                self.provider_name,
                f"Model not found: {self.config.model}. Run: ollama pull {self.config.model}",
            )

        raise LLMProviderError(
            detail,
            self.provider_name,
            status_code=status,
            retryable=status >= 500,
        )
