"""Tests for cache services."""

import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.cache.embedding_cache import EmbeddingCache
from app.services.cache.rate_limiter import RateLimitExceeded, RateLimiter
from app.services.cache.redis_client import RedisClient
from app.services.cache.session_cache import SessionCache
from app.services.cache.types import CachedEmbedding, CacheStats


# Fixtures
@pytest.fixture
def mock_redis_client() -> MagicMock:
    """Create a mock Redis client."""
    client = MagicMock(spec=RedisClient)
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.get_json = AsyncMock(return_value=None)
    client.set_json = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.exists = AsyncMock(return_value=False)
    client.expire = AsyncMock(return_value=True)
    client.scan_keys = AsyncMock(return_value=[])
    client.client = MagicMock()
    return client


# CachedEmbedding Tests
class TestCachedEmbedding:
    """Tests for CachedEmbedding dataclass."""

    def test_to_dict(self):
        """Test serialization to dict."""
        cached = CachedEmbedding(
            embedding=[0.1, 0.2, 0.3],
            model="test-model",
            cached_at=datetime(2024, 1, 1, 12, 0, 0),
        )

        result = cached.to_dict()

        assert result["embedding"] == [0.1, 0.2, 0.3]
        assert result["model"] == "test-model"
        assert result["cached_at"] == "2024-01-01T12:00:00"

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "embedding": [0.1, 0.2, 0.3],
            "model": "test-model",
            "cached_at": "2024-01-01T12:00:00",
        }

        result = CachedEmbedding.from_dict(data)

        assert result.embedding == [0.1, 0.2, 0.3]
        assert result.model == "test-model"
        assert result.cached_at == datetime(2024, 1, 1, 12, 0, 0)

    def test_from_dict_missing_fields(self):
        """Test deserialization with missing fields."""
        data: dict[str, str | list[float]] = {}

        result = CachedEmbedding.from_dict(data)

        assert result.embedding == []
        assert result.model == ""


# CacheStats Tests
class TestCacheStats:
    """Tests for CacheStats dataclass."""

    def test_hit_rate_with_hits_and_misses(self):
        """Test hit rate calculation."""
        stats = CacheStats(hits=75, misses=25, size=100)
        assert stats.hit_rate == 0.75

    def test_hit_rate_no_requests(self):
        """Test hit rate with no requests."""
        stats = CacheStats(hits=0, misses=0, size=0)
        assert stats.hit_rate == 0.0


# EmbeddingCache Tests
class TestEmbeddingCache:
    """Tests for EmbeddingCache."""

    @pytest.mark.asyncio
    async def test_get_embedding_cache_hit(self, mock_redis_client: MagicMock):
        """Test cache hit for embedding."""
        cache = EmbeddingCache(mock_redis_client)

        cached_data = {
            "embedding": [0.1, 0.2, 0.3],
            "model": "test-model",
            "cached_at": "2024-01-01T12:00:00",
        }
        mock_redis_client.get_json.return_value = cached_data

        result = await cache.get_embedding("Hello world", "test-model")

        assert result is not None
        assert result.embedding == [0.1, 0.2, 0.3]
        assert result.model == "test-model"
        assert cache._hits == 1
        assert cache._misses == 0

    @pytest.mark.asyncio
    async def test_get_embedding_cache_miss(self, mock_redis_client: MagicMock):
        """Test cache miss for embedding."""
        cache = EmbeddingCache(mock_redis_client)
        mock_redis_client.get_json.return_value = None

        result = await cache.get_embedding("Hello world", "test-model")

        assert result is None
        assert cache._misses == 1

    @pytest.mark.asyncio
    async def test_set_embedding(self, mock_redis_client: MagicMock):
        """Test storing embedding in cache."""
        cache = EmbeddingCache(mock_redis_client)

        result = await cache.set_embedding(
            text="Hello world",
            embedding=[0.1, 0.2, 0.3],
            model="test-model",
        )

        assert result is True
        mock_redis_client.set_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_embedding_with_custom_ttl(self, mock_redis_client: MagicMock):
        """Test storing embedding with custom TTL."""
        cache = EmbeddingCache(mock_redis_client)

        await cache.set_embedding(
            text="Hello",
            embedding=[0.1],
            model="test",
            ttl=3600,  # 1 hour
        )

        call_args = mock_redis_client.set_json.call_args
        assert call_args.kwargs["ex"] == 3600

    @pytest.mark.asyncio
    async def test_get_batch(self, mock_redis_client: MagicMock):
        """Test batch get with mixed hits/misses."""
        cache = EmbeddingCache(mock_redis_client)

        cached_data = {
            "embedding": [0.1],
            "model": "test",
            "cached_at": "2024-01-01T12:00:00",
        }

        # First call hits, second misses
        mock_redis_client.get_json.side_effect = [cached_data, None]

        results, misses = await cache.get_batch(["Hello", "World"], "test")

        assert len(results) == 2
        assert results[0] is not None
        assert results[1] is None
        assert misses == [1]

    @pytest.mark.asyncio
    async def test_get_stats(self, mock_redis_client: MagicMock):
        """Test getting cache statistics."""
        cache = EmbeddingCache(mock_redis_client)
        cache._hits = 10
        cache._misses = 5

        mock_redis_client.scan_keys.return_value = ["key1", "key2", "key3"]

        stats = await cache.get_stats()

        assert stats.hits == 10
        assert stats.misses == 5
        assert stats.size == 3

    def test_make_key_consistency(self, mock_redis_client: MagicMock):
        """Test key generation is deterministic."""
        cache = EmbeddingCache(mock_redis_client)

        key1 = cache._make_key("Hello world", "test-model")
        key2 = cache._make_key("Hello world", "test-model")

        assert key1 == key2
        assert "test-model" in key1


# SessionCache Tests
class TestSessionCache:
    """Tests for SessionCache."""

    @pytest.mark.asyncio
    async def test_create_session(self, mock_redis_client: MagicMock):
        """Test creating a new session."""
        cache = SessionCache(mock_redis_client)

        session = await cache.create_session(
            conversation_id="conv-123",
            collection_id="coll-456",
            metadata={"user": "test"},
        )

        assert session["conversation_id"] == "conv-123"
        assert session["collection_id"] == "coll-456"
        assert session["messages"] == []
        assert session["metadata"] == {"user": "test"}
        mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_extends_ttl(self, mock_redis_client: MagicMock):
        """Test that getting session extends TTL (sliding window)."""
        cache = SessionCache(mock_redis_client)

        session_data = {
            "conversation_id": "conv-123",
            "collection_id": "coll-456",
            "messages": [],
            "created_at": "2024-01-01T12:00:00",
            "last_activity": "2024-01-01T12:00:00",
            "metadata": {},
        }
        mock_redis_client.get.return_value = (
            '{"conversation_id": "conv-123", "collection_id": "coll-456", '
            '"messages": [], "created_at": "2024-01-01T12:00:00", '
            '"last_activity": "2024-01-01T12:00:00", "metadata": {}}'
        )

        await cache.get_session("conv-123")

        mock_redis_client.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_message(self, mock_redis_client: MagicMock):
        """Test adding message to session."""
        cache = SessionCache(mock_redis_client)

        mock_redis_client.get.return_value = (
            '{"conversation_id": "conv-123", "collection_id": "coll-456", '
            '"messages": [], "created_at": "2024-01-01T12:00:00", '
            '"last_activity": "2024-01-01T12:00:00", "metadata": {}}'
        )

        result = await cache.add_message(
            conversation_id="conv-123",
            role="user",
            content="Hello!",
        )

        assert result is True
        mock_redis_client.set.assert_called()

    @pytest.mark.asyncio
    async def test_add_message_session_not_found(self, mock_redis_client: MagicMock):
        """Test adding message when session doesn't exist."""
        cache = SessionCache(mock_redis_client)
        mock_redis_client.get.return_value = None

        result = await cache.add_message(
            conversation_id="nonexistent",
            role="user",
            content="Hello!",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_max_messages_trim(self, mock_redis_client: MagicMock):
        """Test that messages are trimmed to max_messages."""
        cache = SessionCache(mock_redis_client, max_messages=3)

        # Session with 3 messages already
        existing_messages = [
            {"role": "user", "content": "1", "timestamp": "2024-01-01T12:00:00"},
            {"role": "assistant", "content": "2", "timestamp": "2024-01-01T12:01:00"},
            {"role": "user", "content": "3", "timestamp": "2024-01-01T12:02:00"},
        ]

        import json
        mock_redis_client.get.return_value = json.dumps({
            "conversation_id": "conv-123",
            "collection_id": "coll-456",
            "messages": existing_messages,
            "created_at": "2024-01-01T12:00:00",
            "last_activity": "2024-01-01T12:02:00",
            "metadata": {},
        })

        await cache.add_message("conv-123", "assistant", "4")

        # Check that set was called with trimmed messages
        call_args = mock_redis_client.set.call_args
        saved_data = json.loads(call_args.args[1])
        assert len(saved_data["messages"]) == 3
        assert saved_data["messages"][-1]["content"] == "4"

    @pytest.mark.asyncio
    async def test_get_messages(self, mock_redis_client: MagicMock):
        """Test getting messages from session."""
        cache = SessionCache(mock_redis_client)

        messages = [
            {"role": "user", "content": "Hello", "timestamp": "2024-01-01T12:00:00"},
            {"role": "assistant", "content": "Hi", "timestamp": "2024-01-01T12:00:01"},
        ]

        import json
        mock_redis_client.get.return_value = json.dumps({
            "conversation_id": "conv-123",
            "collection_id": "coll-456",
            "messages": messages,
            "created_at": "2024-01-01T12:00:00",
            "last_activity": "2024-01-01T12:00:01",
            "metadata": {},
        })

        result = await cache.get_messages("conv-123")

        assert len(result) == 2
        assert result[0]["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_get_messages_with_limit(self, mock_redis_client: MagicMock):
        """Test getting limited messages."""
        cache = SessionCache(mock_redis_client)

        messages = [
            {"role": "user", "content": "1", "timestamp": "t1"},
            {"role": "assistant", "content": "2", "timestamp": "t2"},
            {"role": "user", "content": "3", "timestamp": "t3"},
        ]

        import json
        mock_redis_client.get.return_value = json.dumps({
            "conversation_id": "conv-123",
            "collection_id": "coll-456",
            "messages": messages,
            "created_at": "t1",
            "last_activity": "t3",
            "metadata": {},
        })

        result = await cache.get_messages("conv-123", limit=2)

        assert len(result) == 2
        assert result[0]["content"] == "2"
        assert result[1]["content"] == "3"


# RateLimiter Tests
class TestRateLimiter:
    """Tests for RateLimiter."""

    @pytest.mark.asyncio
    async def test_check_under_limit(self, mock_redis_client: MagicMock):
        """Test checking rate limit when under limit."""
        limiter = RateLimiter(mock_redis_client, default_limit=10)

        mock_redis_client.client.zremrangebyscore = AsyncMock()
        mock_redis_client.client.zcard = AsyncMock(return_value=5)

        result = await limiter.check("user-123")

        assert result.allowed is True
        assert result.remaining == 5
        assert result.limit == 10

    @pytest.mark.asyncio
    async def test_check_at_limit(self, mock_redis_client: MagicMock):
        """Test checking rate limit when at limit."""
        limiter = RateLimiter(mock_redis_client, default_limit=10)

        mock_redis_client.client.zremrangebyscore = AsyncMock()
        mock_redis_client.client.zcard = AsyncMock(return_value=10)

        result = await limiter.check("user-123")

        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after == 60  # default window

    @pytest.mark.asyncio
    async def test_acquire_success(self, mock_redis_client: MagicMock):
        """Test acquiring rate limit slot successfully."""
        limiter = RateLimiter(mock_redis_client, default_limit=10)

        # Lua script returns [1, 6] - allowed with 6 total requests
        mock_redis_client.client.eval = AsyncMock(return_value=[1, 6])

        result = await limiter.acquire("user-123")

        assert result.allowed is True
        assert result.remaining == 4

    @pytest.mark.asyncio
    async def test_acquire_limit_exceeded(self, mock_redis_client: MagicMock):
        """Test acquiring when limit exceeded raises exception."""
        limiter = RateLimiter(mock_redis_client, default_limit=10)

        # Lua script returns [0, 10] - not allowed
        mock_redis_client.client.eval = AsyncMock(return_value=[0, 10])
        mock_redis_client.client.zrange = AsyncMock(
            return_value=[("1234567890.0:1", time.time() - 30)]
        )

        with pytest.raises(RateLimitExceeded) as exc_info:
            await limiter.acquire("user-123")

        assert exc_info.value.limit == 10
        assert exc_info.value.retry_after > 0

    @pytest.mark.asyncio
    async def test_acquire_with_cost(self, mock_redis_client: MagicMock):
        """Test acquiring multiple slots at once."""
        limiter = RateLimiter(mock_redis_client, default_limit=10)

        mock_redis_client.client.eval = AsyncMock(return_value=[1, 5])

        result = await limiter.acquire("user-123", cost=5)

        assert result.allowed is True
        # Verify eval was called with cost=5
        call_args = mock_redis_client.client.eval.call_args
        assert str(5) in call_args.args

    @pytest.mark.asyncio
    async def test_reset(self, mock_redis_client: MagicMock):
        """Test resetting rate limit for user."""
        limiter = RateLimiter(mock_redis_client)

        mock_redis_client.delete.return_value = 1

        result = await limiter.reset("user-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_get_usage(self, mock_redis_client: MagicMock):
        """Test getting current usage."""
        limiter = RateLimiter(mock_redis_client)

        mock_redis_client.client.zremrangebyscore = AsyncMock()
        mock_redis_client.client.zcard = AsyncMock(return_value=7)

        usage = await limiter.get_usage("user-123")

        assert usage == 7

    def test_make_key_with_resource(self, mock_redis_client: MagicMock):
        """Test key generation with resource."""
        limiter = RateLimiter(mock_redis_client)

        key = limiter._make_key("user-123", "chat")

        assert "ratelimit" in key
        assert "chat" in key
        assert "user-123" in key


class TestRateLimitExceeded:
    """Tests for RateLimitExceeded exception."""

    def test_exception_message(self):
        """Test exception message format."""
        exc = RateLimitExceeded(limit=60, window=60, retry_after=30.5)

        assert "60 requests per 60s" in str(exc)
        assert "30.5s" in str(exc)

    def test_exception_attributes(self):
        """Test exception attributes."""
        exc = RateLimitExceeded(limit=100, window=120, retry_after=45.0)

        assert exc.limit == 100
        assert exc.window == 120
        assert exc.retry_after == 45.0
