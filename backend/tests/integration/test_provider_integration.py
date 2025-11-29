"""Integration tests for LLM and Embedding providers with real Ollama."""

import pytest
import pytest_asyncio

from app.providers.embedding.ollama import OllamaEmbeddingProvider
from app.providers.embedding.types import EmbeddingConfig
from app.providers.llm.ollama import OllamaProvider
from app.providers.llm.types import LLMConfig


def is_ollama_available() -> bool:
    """Check if Ollama is available."""
    import httpx

    try:
        response = httpx.get("http://ollama:11434/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def is_model_available(model: str) -> bool:
    """Check if a specific model is available in Ollama."""
    import httpx

    try:
        response = httpx.get("http://ollama:11434/api/tags", timeout=5)
        if response.status_code != 200:
            return False
        models = response.json().get("models", [])
        return any(m.get("name", "").startswith(model) for m in models)
    except Exception:
        return False


# Skip all tests in this module if Ollama is not available
pytestmark = pytest.mark.skipif(
    not is_ollama_available(),
    reason="Ollama not available",
)

# Markers for specific model requirements
requires_llama = pytest.mark.skipif(
    not is_model_available("llama"),
    reason="llama model not available (run: ollama pull llama3.2)",
)

requires_nomic = pytest.mark.skipif(
    not is_model_available("nomic-embed-text"),
    reason="nomic-embed-text not available (run: ollama pull nomic-embed-text)",
)


@requires_llama
class TestOllamaProviderIntegration:
    """Integration tests for OllamaProvider with real Ollama."""

    @pytest_asyncio.fixture
    async def provider(self) -> OllamaProvider:
        """Create Ollama provider for testing."""
        config = LLMConfig(
            model="llama3.2",
            temperature=0.7,
            max_tokens=100,
        )
        return OllamaProvider(config, base_url="http://ollama:11434")

    @pytest.mark.asyncio
    async def test_health_check(self, provider: OllamaProvider):
        """Test that Ollama is responding."""
        is_healthy = await provider.health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_generate_simple(self, provider: OllamaProvider):
        """Test simple text generation."""
        messages = [{"role": "user", "content": "Say 'hello' and nothing else."}]

        response = await provider.generate(messages)

        assert response.content is not None
        assert len(response.content) > 0
        assert response.model is not None

    @pytest.mark.asyncio
    async def test_generate_with_system_prompt(self, provider: OllamaProvider):
        """Test generation with system prompt."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Be brief."},
            {"role": "user", "content": "What is 2+2?"},
        ]

        response = await provider.generate(messages)

        assert response.content is not None
        assert "4" in response.content

    @pytest.mark.asyncio
    async def test_generate_conversation(self, provider: OllamaProvider):
        """Test multi-turn conversation."""
        messages = [
            {"role": "user", "content": "My name is Alice."},
            {"role": "assistant", "content": "Hello Alice! Nice to meet you."},
            {"role": "user", "content": "What is my name?"},
        ]

        response = await provider.generate(messages)

        assert response.content is not None
        assert "Alice" in response.content

    @pytest.mark.asyncio
    async def test_streaming(self, provider: OllamaProvider):
        """Test streaming generation."""
        messages = [{"role": "user", "content": "Count from 1 to 5."}]

        chunks = []
        async for chunk in provider.generate_stream(messages):
            chunks.append(chunk)

        assert len(chunks) > 0
        # Combine all chunks
        full_content = "".join(c.content for c in chunks if c.content)
        assert len(full_content) > 0

    @pytest.mark.asyncio
    async def test_token_counting(self, provider: OllamaProvider):
        """Test that tokens are counted."""
        messages = [{"role": "user", "content": "Hello!"}]

        response = await provider.generate(messages)

        # Ollama should return token counts
        assert response.tokens_input >= 0
        assert response.tokens_output >= 0


@requires_nomic
class TestOllamaEmbeddingProviderIntegration:
    """Integration tests for OllamaEmbeddingProvider with real Ollama."""

    @pytest_asyncio.fixture
    async def provider(self) -> OllamaEmbeddingProvider:
        """Create Ollama embedding provider for testing."""
        config = EmbeddingConfig(
            model="nomic-embed-text",
            dimension=768,
        )
        return OllamaEmbeddingProvider(config, base_url="http://ollama:11434")

    @pytest.mark.asyncio
    async def test_health_check(self, provider: OllamaEmbeddingProvider):
        """Test that Ollama embedding endpoint is responding."""
        is_healthy = await provider.health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_embed_single(self, provider: OllamaEmbeddingProvider):
        """Test embedding a single text."""
        result = await provider.embed("Hello, world!")

        assert result.embedding is not None
        assert len(result.embedding) == 768
        assert result.model == "nomic-embed-text"

    @pytest.mark.asyncio
    async def test_embed_batch(self, provider: OllamaEmbeddingProvider):
        """Test batch embedding."""
        texts = [
            "First document about Python.",
            "Second document about JavaScript.",
            "Third document about databases.",
        ]

        result = await provider.embed_batch(texts)

        assert len(result.embeddings) == 3
        assert all(len(emb) == 768 for emb in result.embeddings)

    @pytest.mark.asyncio
    async def test_similar_texts_have_similar_embeddings(
        self,
        provider: OllamaEmbeddingProvider,
    ):
        """Test that semantically similar texts produce similar embeddings."""
        import math

        def cosine_similarity(a: list[float], b: list[float]) -> float:
            dot_product = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            return dot_product / (norm_a * norm_b)

        # Similar texts
        text1 = "The cat sat on the mat."
        text2 = "A cat is sitting on a mat."
        # Different text
        text3 = "The stock market crashed today."

        result1 = await provider.embed(text1)
        result2 = await provider.embed(text2)
        result3 = await provider.embed(text3)

        sim_12 = cosine_similarity(result1.embedding, result2.embedding)
        sim_13 = cosine_similarity(result1.embedding, result3.embedding)

        # Similar texts should have higher similarity
        assert sim_12 > sim_13
        # Similar texts should be quite similar (>0.7)
        assert sim_12 > 0.7

    @pytest.mark.asyncio
    async def test_empty_text_handling(self, provider: OllamaEmbeddingProvider):
        """Test embedding empty or whitespace text."""
        # This tests that the provider handles edge cases
        result = await provider.embed("   ")

        # Should still return an embedding
        assert result.embedding is not None
        assert len(result.embedding) == 768

    @pytest.mark.asyncio
    async def test_long_text(self, provider: OllamaEmbeddingProvider):
        """Test embedding longer text."""
        long_text = "This is a test. " * 100  # ~1600 characters

        result = await provider.embed(long_text)

        assert result.embedding is not None
        assert len(result.embedding) == 768

    @pytest.mark.asyncio
    async def test_unicode_text(self, provider: OllamaEmbeddingProvider):
        """Test embedding text with unicode characters."""
        unicode_text = "Olá mundo! 你好世界! مرحبا بالعالم!"

        result = await provider.embed(unicode_text)

        assert result.embedding is not None
        assert len(result.embedding) == 768


@requires_llama
@requires_nomic
class TestProviderInteraction:
    """Test LLM and Embedding providers working together."""

    @pytest.mark.asyncio
    async def test_rag_pipeline_simulation(self):
        """Simulate a simple RAG pipeline."""
        # Create providers
        llm_config = LLMConfig(model="llama3.2", max_tokens=200)
        embed_config = EmbeddingConfig(model="nomic-embed-text", dimension=768)

        llm = OllamaProvider(llm_config, base_url="http://ollama:11434")
        embedder = OllamaEmbeddingProvider(embed_config, base_url="http://ollama:11434")

        # Simulate document chunks
        documents = [
            "Python is a programming language created by Guido van Rossum.",
            "JavaScript is primarily used for web development.",
            "PostgreSQL is a powerful relational database.",
        ]

        # Generate embeddings for documents
        doc_embeddings = await embedder.embed_batch(documents)
        assert len(doc_embeddings.embeddings) == 3

        # Simulate query
        query = "Who created Python?"
        query_embedding = await embedder.embed(query)

        # Find most similar (simple cosine similarity)
        import math

        def cosine_sim(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            return dot / (norm_a * norm_b)

        similarities = [
            cosine_sim(query_embedding.embedding, doc_emb)
            for doc_emb in doc_embeddings.embeddings
        ]

        # Most relevant should be the Python document (index 0)
        most_relevant_idx = similarities.index(max(similarities))
        context = documents[most_relevant_idx]

        # Generate answer with context
        messages = [
            {
                "role": "system",
                "content": f"Answer based on this context: {context}",
            },
            {"role": "user", "content": query},
        ]

        response = await llm.generate(messages)

        assert response.content is not None
        assert "Guido" in response.content
