"""OpenAI LLM provider implementation."""

from collections.abc import AsyncIterator

from openai import AsyncOpenAI, APIConnectionError, APIStatusError, RateLimitError, AuthenticationError

from app.providers.llm.base import BaseLLMProvider
from app.providers.llm.exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMInvalidRequestError,
    LLMProviderError,
    LLMRateLimitError,
)
from app.providers.llm.types import (
    ChatMessage,
    LLMConfig,
    LLMResponse,
    StreamChunk,
)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider.

    Uses the official OpenAI Python SDK for chat completions.
    Supports streaming responses.
    """

    def __init__(
        self,
        config: LLMConfig,
        api_key: str,
        timeout: float = 60.0,
    ):
        """Initialize OpenAI provider.

        Args:
            config: LLM configuration.
            api_key: OpenAI API key.
            timeout: Request timeout in seconds.
        """
        super().__init__(config)
        self.client = AsyncOpenAI(api_key=api_key, timeout=timeout)

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """Generate a complete response from OpenAI.

        Args:
            messages: Chat messages.
            temperature: Override temperature.
            max_tokens: Override max tokens.

        Returns:
            LLMResponse with content and metadata.
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[dict(m) for m in messages],  # type: ignore[misc]
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                top_p=self.config.top_p,
                stop=self.config.stop_sequences or None,
                stream=False,
            )

            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                tokens_input=usage.prompt_tokens if usage else 0,
                tokens_output=usage.completion_tokens if usage else 0,
                finish_reason=choice.finish_reason,
            )

        except AuthenticationError as e:
            raise LLMAuthenticationError(self.provider_name) from e
        except RateLimitError as e:
            raise LLMRateLimitError(self.provider_name) from e
        except APIConnectionError as e:
            raise LLMConnectionError(self.provider_name, str(e)) from e
        except APIStatusError as e:
            self._handle_api_error(e)

    async def generate_stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Generate a streaming response from OpenAI.

        Args:
            messages: Chat messages.
            temperature: Override temperature.
            max_tokens: Override max tokens.

        Yields:
            StreamChunk with partial content.
        """
        try:
            stream = await self.client.chat.completions.create(
                model=self.config.model,
                messages=[dict(m) for m in messages],  # type: ignore[misc]
                temperature=temperature or self.config.temperature,
                max_tokens=max_tokens or self.config.max_tokens,
                top_p=self.config.top_p,
                stop=self.config.stop_sequences or None,
                stream=True,
            )

            async for chunk in stream:
                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                content = delta.content or ""
                is_final = choice.finish_reason is not None

                if content or is_final:
                    yield StreamChunk(
                        content=content,
                        is_final=is_final,
                        finish_reason=choice.finish_reason,
                    )

        except AuthenticationError as e:
            raise LLMAuthenticationError(self.provider_name) from e
        except RateLimitError as e:
            raise LLMRateLimitError(self.provider_name) from e
        except APIConnectionError as e:
            raise LLMConnectionError(self.provider_name, str(e)) from e
        except APIStatusError as e:
            self._handle_api_error(e)

    async def health_check(self) -> bool:
        """Check if OpenAI API is available.

        Returns:
            True if API is responding with valid credentials.
        """
        try:
            # List models as a lightweight health check
            await self.client.models.list()
            return True
        except Exception:
            return False

    def _handle_api_error(self, error: APIStatusError) -> None:
        """Handle API errors from OpenAI.

        Args:
            error: The API error.

        Raises:
            LLMProviderError: Appropriate exception for the error.
        """
        status = error.status_code
        message = str(error.message) if hasattr(error, "message") else str(error)

        if status == 400:
            raise LLMInvalidRequestError(self.provider_name, message)

        raise LLMProviderError(
            message,
            self.provider_name,
            status_code=status,
            retryable=status >= 500,
        )
