"""Tests for embedding providers."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.providers.embedding.exceptions import (
    EmbeddingConnectionError,
    EmbeddingInvalidRequestError,
)
from app.providers.embedding.factory import create_embedding_provider
from app.providers.embedding.ollama import OllamaEmbeddingProvider
from app.providers.embedding.openai import OpenAIEmbeddingProvider
from app.providers.embedding.types import EmbeddingConfig


# Fixtures
@pytest.fixture
def embedding_config() -> EmbeddingConfig:
    """Default embedding configuration."""
    return EmbeddingConfig(
        model="test-model",
        dimension=768,
    )


# OllamaEmbeddingProvider Tests
class TestOllamaEmbeddingProvider:
    """Tests for OllamaEmbeddingProvider."""

    @pytest.mark.asyncio
    async def test_embed_success(self, embedding_config: EmbeddingConfig):
        """Test successful embedding generation."""
        provider = OllamaEmbeddingProvider(
            embedding_config,
            base_url="http://test:11434",
        )

        mock_embedding = [0.1] * 768
        mock_response = {"embedding": mock_embedding}

        with patch.object(httpx.AsyncClient, "post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=MagicMock(return_value=mock_response),
                raise_for_status=MagicMock(),
            )

            result = await provider.embed("Hello world")

            assert len(result.embedding) == 768
            assert result.model == "test-model"

    @pytest.mark.asyncio
    async def test_embed_batch_success(self, embedding_config: EmbeddingConfig):
        """Test successful batch embedding."""
        provider = OllamaEmbeddingProvider(
            embedding_config,
            base_url="http://test:11434",
        )

        mock_embedding = [0.1] * 768
        mock_response = {"embedding": mock_embedding}

        with patch.object(httpx.AsyncClient, "post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=MagicMock(return_value=mock_response),
                raise_for_status=MagicMock(),
            )

            result = await provider.embed_batch(["Hello", "World"])

            assert len(result.embeddings) == 2
            assert all(len(e) == 768 for e in result.embeddings)

    @pytest.mark.asyncio
    async def test_embed_connection_error(self, embedding_config: EmbeddingConfig):
        """Test connection error handling."""
        provider = OllamaEmbeddingProvider(
            embedding_config,
            base_url="http://test:11434",
        )

        with patch.object(httpx.AsyncClient, "post") as mock_post:
            mock_post.side_effect = httpx.ConnectError("Connection refused")

            with pytest.raises(EmbeddingConnectionError) as exc_info:
                await provider.embed("Hello")

            assert exc_info.value.provider == "ollama"
            assert exc_info.value.retryable is True

    @pytest.mark.asyncio
    async def test_embed_model_not_found(self, embedding_config: EmbeddingConfig):
        """Test model not found error."""
        provider = OllamaEmbeddingProvider(
            embedding_config,
            base_url="http://test:11434",
        )

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

            with pytest.raises(EmbeddingInvalidRequestError) as exc_info:
                await provider.embed("Hello")

            assert "Model not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_health_check_success(self, embedding_config: EmbeddingConfig):
        """Test successful health check."""
        provider = OllamaEmbeddingProvider(
            embedding_config,
            base_url="http://test:11434",
        )

        with patch.object(httpx.AsyncClient, "get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)

            result = await provider.health_check()

            assert result is True

    def test_provider_name(self, embedding_config: EmbeddingConfig):
        """Test provider name property."""
        provider = OllamaEmbeddingProvider(embedding_config)
        assert provider.provider_name == "ollama"

    def test_dimension_property(self, embedding_config: EmbeddingConfig):
        """Test dimension property."""
        provider = OllamaEmbeddingProvider(embedding_config)
        assert provider.dimension == 768


# OpenAIEmbeddingProvider Tests
class TestOpenAIEmbeddingProvider:
    """Tests for OpenAIEmbeddingProvider."""

    @pytest.mark.asyncio
    async def test_embed_success(self, embedding_config: EmbeddingConfig):
        """Test successful embedding generation."""
        provider = OpenAIEmbeddingProvider(embedding_config, api_key="test-key")

        mock_embedding = [0.1] * 768
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        mock_response.model = "test-model"
        mock_response.usage = MagicMock(total_tokens=10)

        with patch.object(
            provider.client.embeddings,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await provider.embed("Hello world")

            assert len(result.embedding) == 768
            assert result.tokens_used == 10

    @pytest.mark.asyncio
    async def test_embed_batch_success(self, embedding_config: EmbeddingConfig):
        """Test successful batch embedding."""
        provider = OpenAIEmbeddingProvider(embedding_config, api_key="test-key")

        mock_embedding = [0.1] * 768
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=mock_embedding, index=0),
            MagicMock(embedding=mock_embedding, index=1),
        ]
        mock_response.model = "test-model"
        mock_response.usage = MagicMock(total_tokens=20)

        with patch.object(
            provider.client.embeddings,
            "create",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await provider.embed_batch(["Hello", "World"])

            assert len(result.embeddings) == 2
            assert result.total_tokens == 20

    def test_provider_name(self, embedding_config: EmbeddingConfig):
        """Test provider name property."""
        provider = OpenAIEmbeddingProvider(embedding_config, api_key="test-key")
        assert provider.provider_name == "openai"


# Factory Tests
class TestEmbeddingFactory:
    """Tests for embedding factory."""

    def test_create_ollama_provider(self):
        """Test creating Ollama embedding provider."""
        with patch("app.providers.embedding.factory.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                embedding_provider="ollama",
                ollama_base_url="http://localhost:11434",
                embedding_model="nomic-embed-text",
                embedding_dimension=768,
            )

            provider = create_embedding_provider("ollama")

            assert isinstance(provider, OllamaEmbeddingProvider)
            assert provider.provider_name == "ollama"

    def test_create_openai_provider(self):
        """Test creating OpenAI embedding provider."""
        with patch("app.providers.embedding.factory.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                embedding_provider="openai",
                openai_api_key="test-key",
                openai_embedding_model="text-embedding-3-small",
            )

            provider = create_embedding_provider("openai")

            assert isinstance(provider, OpenAIEmbeddingProvider)
            assert provider.provider_name == "openai"

    def test_create_openai_without_key_raises(self):
        """Test that creating OpenAI without key raises error."""
        with patch("app.providers.embedding.factory.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                embedding_provider="openai",
                openai_api_key=None,
            )

            with pytest.raises(ValueError) as exc_info:
                create_embedding_provider("openai")

            assert "API key is required" in str(exc_info.value)
