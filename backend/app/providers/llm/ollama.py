"""Ollama LLM provider implementation."""

import json
import logging
from collections.abc import AsyncIterator

import httpx

from app.providers.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)
from app.providers.llm.exceptions import (
    LLMConnectionError,
    LLMInvalidRequestError,
    LLMProviderError,
)
from app.providers.llm.types import (
    ChatMessage,
    LLMConfig,
    LLMResponse,
    LLMResponseWithTools,
    StreamChunk,
    ToolCall,
    ToolDefinition,
    ToolMessage,
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

    # Models that support tool calling in Ollama
    TOOL_CALLING_MODELS = frozenset({
        "qwen3",
        "qwen2.5",
        "llama3.1",
        "llama3.2",
        "mistral",
        "mixtral",
        "command-r",
        "command-r-plus",
    })

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def supports_tool_calling(self) -> bool:
        """Check if current model supports tool calling.

        Returns:
            True if model supports tool calling.
        """
        model_base = self.config.model.split(":")[0].lower()
        return any(model_base.startswith(m) for m in self.TOOL_CALLING_MODELS)

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
                            # Extract token counts from final chunk
                            tokens_input = None
                            tokens_output = None
                            if is_done:
                                tokens_input = data.get("prompt_eval_count")
                                tokens_output = data.get("eval_count")

                            yield StreamChunk(
                                content=content,
                                is_final=is_done,
                                finish_reason=data.get("done_reason"),
                                tokens_input=tokens_input,
                                tokens_output=tokens_output,
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

    async def generate_with_tools(
        self,
        messages: list[ChatMessage | ToolMessage],
        tools: list[ToolDefinition],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponseWithTools:
        """Generate a response with potential tool calls.

        Uses Ollama's native tool calling support for compatible models.

        Args:
            messages: Chat messages including tool results.
            tools: Available tools for the LLM to call.
            temperature: Override temperature.
            max_tokens: Override max tokens.

        Returns:
            LLMResponseWithTools with content and/or tool calls.
        """
        if not self.supports_tool_calling:
            raise NotImplementedError(
                f"Model {self.config.model} does not support tool calling. "
                "Use qwen3, llama3.1+, mistral, or command-r models."
            )

        payload = self._build_payload_with_tools(
            messages,
            tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        logger.debug(
            "Ollama request with %d tools: %s",
            len(tools),
            [t.get("function", {}).get("name") for t in tools],
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                logger.debug(
                    "Ollama raw response message: %s",
                    json.dumps(data.get("message", {}), indent=2)[:1000],
                )

                return self._parse_tool_response(data)

            except httpx.ConnectError as e:
                raise LLMConnectionError(self.provider_name, str(e)) from e
            except httpx.HTTPStatusError as e:
                self._handle_http_error(e)
            except httpx.TimeoutException as e:
                raise LLMConnectionError(
                    self.provider_name,
                    f"Request timed out after {self.timeout}s",
                ) from e

        # This should never be reached but satisfies type checker
        raise LLMProviderError("Unexpected error", self.provider_name)

    def _build_payload_with_tools(
        self,
        messages: list[ChatMessage | ToolMessage],
        tools: list[ToolDefinition],
        *,
        temperature: float | None,
        max_tokens: int | None,
    ) -> dict[str, object]:
        """Build payload for tool calling request.

        Args:
            messages: Chat messages.
            tools: Tool definitions.
            temperature: Temperature override.
            max_tokens: Max tokens override.

        Returns:
            Request payload dictionary.
        """
        # Convert messages to Ollama format
        formatted_messages = []
        for msg in messages:
            if msg.get("role") == "tool":
                # Tool result message
                formatted_messages.append({
                    "role": "tool",
                    "content": msg.get("content", ""),
                })
            else:
                formatted_messages.append(dict(msg))

        return {
            "model": self.config.model,
            "messages": formatted_messages,
            "tools": tools,
            "stream": False,
            "options": {
                "temperature": temperature or self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
                "top_p": self.config.top_p,
                "num_ctx": self.config.context_window_tools,
            },
        }

    def _parse_tool_response(self, data: dict[str, object]) -> LLMResponseWithTools:
        """Parse Ollama response with potential tool calls.

        Args:
            data: Raw response from Ollama API.

        Returns:
            Parsed LLMResponseWithTools.
        """
        message = data.get("message", {})
        content = message.get("content")
        raw_tool_calls = message.get("tool_calls")

        # Filter out qwen3 "thinking" content that may leak into response
        if content:
            # Remove </think> tags and content before them
            if "</think>" in content:
                content = content.split("</think>")[-1].strip()
            # Remove content that looks like thinking output (starts with special chars)
            if content and content[0] in "Ɛ\ue000\uf000":
                # Find where actual content starts (after thinking block)
                for marker in ["</think>", "\n\n", "---"]:
                    if marker in content:
                        content = content.split(marker)[-1].strip()
                        break

        # Parse tool calls if present
        tool_calls: list[ToolCall] | None = None
        if raw_tool_calls:
            tool_calls = []
            for i, tc in enumerate(raw_tool_calls):
                func = tc.get("function", {})
                tool_calls.append(
                    ToolCall(
                        id=f"call_{i}",
                        name=func.get("name", ""),
                        arguments=func.get("arguments", {}),
                    )
                )

        return LLMResponseWithTools(
            content=content if content else None,
            tool_calls=tool_calls,
            model=data.get("model", self.config.model),
            tokens_input=data.get("prompt_eval_count", 0),
            tokens_output=data.get("eval_count", 0),
            finish_reason=data.get("done_reason"),
        )

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
                "num_ctx": self.config.context_window,
                "num_batch": 512,  # Batch size for prompt processing
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
