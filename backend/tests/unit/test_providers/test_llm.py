"""Tests for LLM providers."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.providers.llm.exceptions import LLMConnectionError, LLMInvalidRequestError
from app.providers.llm.factory import create_llm_provider
from app.providers.llm.ollama import OllamaProvider
from app.providers.llm.openai import OpenAIProvider
from app.providers.llm.types import (
    ChatMessage,
    LLMConfig,
    ToolCall,
    ToolDefinition,
)


# Fixtures
@pytest.fixture
def llm_config() -> LLMConfig:
    """Default LLM configuration."""
    return LLMConfig(
        model="test-model",
        temperature=0.7,
        max_tokens=100,
    )


@pytest.fixture
def sample_messages() -> list[ChatMessage]:
    """Sample chat messages."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ]


@pytest.fixture
def sample_tools() -> list[ToolDefinition]:
    """Sample tool definitions for testing."""
    return [
        {
            "type": "function",
            "function": {
                "name": "search_code",
                "description": "Search for code in the repository",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "The search pattern",
                        }
                    },
                    "required": ["pattern"],
                },
            },
        }
    ]


@pytest.fixture
def tool_calling_config() -> LLMConfig:
    """LLM config for a model that supports tool calling."""
    return LLMConfig(
        model="qwen3:8b",
        temperature=0.7,
        max_tokens=512,
    )


# OllamaProvider Tests
class TestOllamaProvider:
    """Tests for OllamaProvider."""

    @pytest.mark.asyncio
    async def test_generate_success(
        self,
        llm_config: LLMConfig,
        sample_messages: list[ChatMessage],
    ):
        """Test successful generation."""
        provider = OllamaProvider(llm_config, base_url="http://test:11434")

        mock_response = {
            "message": {"content": "Hello! How can I help?"},
            "model": "test-model",
            "prompt_eval_count": 10,
            "eval_count": 5,
            "done_reason": "stop",
        }

        with patch.object(httpx.AsyncClient, "post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=MagicMock(return_value=mock_response),
                raise_for_status=MagicMock(),
            )

            response = await provider.generate(sample_messages)

            assert response.content == "Hello! How can I help?"
            assert response.model == "test-model"
            assert response.tokens_input == 10
            assert response.tokens_output == 5

    @pytest.mark.asyncio
    async def test_generate_connection_error(
        self,
        llm_config: LLMConfig,
        sample_messages: list[ChatMessage],
    ):
        """Test connection error handling."""
        provider = OllamaProvider(llm_config, base_url="http://test:11434")

        with patch.object(httpx.AsyncClient, "post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            with pytest.raises(LLMConnectionError) as exc_info:
                await provider.generate(sample_messages)

            assert exc_info.value.provider == "ollama"
            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_generate_model_not_found(
        self,
        llm_config: LLMConfig,
        sample_messages: list[ChatMessage],
    ):
        """Test model not found error."""
        provider = OllamaProvider(llm_config, base_url="http://test:11434")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "model not found"}

        with patch.object(httpx.AsyncClient, "post") as mock_post:
            mock_post.return_value = mock_response
            mock_post.return_value.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response,
            )

            with pytest.raises(LLMInvalidRequestError) as exc_info:
                await provider.generate(sample_messages)

            assert "Model not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_success(self, llm_config: LLMConfig):
        """Test successful health check."""
        provider = OllamaProvider(llm_config, base_url="http://test:11434")

        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)

            result = await provider.health_check()

            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, llm_config: LLMConfig):
        """Test failed health check."""
        provider = OllamaProvider(llm_config, base_url="http://test:11434")

        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")

            result = await provider.health_check()

            assert result is False

    def test_provider_name(self, llm_config: LLMConfig):
        """Test provider name property."""
        provider = OllamaProvider(llm_config)
        assert provider.provider_name == "ollama"

    def test_supports_tool_calling_qwen3(self, tool_calling_config: LLMConfig):
        """Test that qwen3 model supports tool calling."""
        provider = OllamaProvider(tool_calling_config)
        assert provider.supports_tool_calling is True

    def test_supports_tool_calling_llama31(self):
        """Test that llama3.1 model supports tool calling."""
        config = LLMConfig(model="llama3.1:8b")
        provider = OllamaProvider(config)
        assert provider.supports_tool_calling is True

    def test_does_not_support_tool_calling_old_model(self):
        """Test that old models don't support tool calling."""
        config = LLMConfig(model="phi3:mini")
        provider = OllamaProvider(config)
        assert provider.supports_tool_calling is False

    @pytest.mark.asyncio
    async def test_generate_with_tools_returns_tool_call(
        self,
        tool_calling_config: LLMConfig,
        sample_messages: list[ChatMessage],
        sample_tools: list[ToolDefinition],
    ):
        """Test generate_with_tools returns tool calls when LLM requests them."""
        provider = OllamaProvider(tool_calling_config, base_url="http://test:11434")

        mock_response = {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "search_code",
                            "arguments": {"pattern": "logo"},
                        }
                    }
                ],
            },
            "model": "qwen3:8b",
            "prompt_eval_count": 50,
            "eval_count": 10,
            "done_reason": "tool_calls",
        }

        with patch.object(httpx.AsyncClient, "post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=MagicMock(return_value=mock_response),
                raise_for_status=MagicMock(),
            )

            response = await provider.generate_with_tools(
                sample_messages, sample_tools
            )

            assert response.has_tool_calls is True
            assert response.tool_calls is not None
            assert len(response.tool_calls) == 1
            assert response.tool_calls[0].name == "search_code"
            assert response.tool_calls[0].arguments == {"pattern": "logo"}

    @pytest.mark.asyncio
    async def test_generate_with_tools_returns_content_when_no_tools_needed(
        self,
        tool_calling_config: LLMConfig,
        sample_messages: list[ChatMessage],
        sample_tools: list[ToolDefinition],
    ):
        """Test generate_with_tools returns content when no tool calls are needed."""
        provider = OllamaProvider(tool_calling_config, base_url="http://test:11434")

        mock_response = {
            "message": {
                "content": "The logo is located in src/assets/logo.png",
            },
            "model": "qwen3:8b",
            "prompt_eval_count": 50,
            "eval_count": 20,
            "done_reason": "stop",
        }

        with patch.object(httpx.AsyncClient, "post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=MagicMock(return_value=mock_response),
                raise_for_status=MagicMock(),
            )

            response = await provider.generate_with_tools(
                sample_messages, sample_tools
            )

            assert response.is_final_response is True
            assert response.content == "The logo is located in src/assets/logo.png"
            assert response.has_tool_calls is False

    @pytest.mark.asyncio
    async def test_generate_with_tools_raises_for_unsupported_model(
        self,
        llm_config: LLMConfig,
        sample_messages: list[ChatMessage],
        sample_tools: list[ToolDefinition],
    ):
        """Test generate_with_tools raises NotImplementedError for unsupported models."""
        # llm_config uses "test-model" which doesn't support tool calling
        provider = OllamaProvider(llm_config, base_url="http://test:11434")

        with pytest.raises(NotImplementedError) as exc_info:
            await provider.generate_with_tools(sample_messages, sample_tools)

        assert "does not support tool calling" in str(exc_info.value)


# OpenAIProvider Tests
class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    @pytest.mark.asyncio
    async def test_generate_success(
        self,
        llm_config: LLMConfig,
        sample_messages: list[ChatMessage],
    ):
        """Test successful generation."""
        provider = OpenAIProvider(llm_config, api_key="test-key")

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content="Hello! How can I help?"),
                finish_reason="stop",
            )
        ]
        mock_response.model = "test-model"
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

        with patch.object(
            provider.client.chat.completions,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = mock_response

            response = await provider.generate(sample_messages)

            assert response.content == "Hello! How can I help?"
            assert response.model == "test-model"
            assert response.tokens_input == 10
            assert response.tokens_output == 5

    def test_provider_name(self, llm_config: LLMConfig):
        """Test provider name property."""
        provider = OpenAIProvider(llm_config, api_key="test-key")
        assert provider.provider_name == "openai"


# Factory Tests
class TestLLMFactory:
    """Tests for LLM factory."""

    def test_create_ollama_provider(self):
        """Test creating Ollama provider."""
        with patch("app.providers.llm.factory.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                llm_provider="ollama",
                ollama_base_url="http://localhost:11434",
                ollama_model="llama3.2",
            )

            provider = create_llm_provider("ollama")

            assert isinstance(provider, OllamaProvider)
            assert provider.provider_name == "ollama"

    def test_create_openai_provider(self):
        """Test creating OpenAI provider."""
        with patch("app.providers.llm.factory.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                llm_provider="openai",
                openai_api_key="test-key",
                openai_model="gpt-4o-mini",
            )

            provider = create_llm_provider("openai")

            assert isinstance(provider, OpenAIProvider)
            assert provider.provider_name == "openai"

    def test_create_openai_without_key_raises(self):
        """Test that creating OpenAI without key raises error."""
        with patch("app.providers.llm.factory.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                llm_provider="openai",
                openai_api_key=None,
                openai_model="gpt-4o-mini",
            )

            with pytest.raises(ValueError) as exc_info:
                create_llm_provider("openai")

            assert "API key is required" in str(exc_info.value)

    def test_create_invalid_provider_raises(self):
        """Test that invalid provider raises error."""
        with patch("app.providers.llm.factory.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(llm_provider="invalid")

            with pytest.raises(ValueError) as exc_info:
                create_llm_provider("invalid")  # type: ignore

            assert "Unknown provider" in str(exc_info.value)
