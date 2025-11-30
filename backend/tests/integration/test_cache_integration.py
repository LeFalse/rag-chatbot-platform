"""Integration tests for cache services with real Redis."""

import asyncio
import time

import pytest
import pytest_asyncio

from app.services.cache.embedding_cache import EmbeddingCache
from app.services.cache.rate_limiter import RateLimitExceeded, RateLimiter
from app.services.cache.redis_client import RedisClient
from app.services.cache.session_cache import SessionCache


@pytest_asyncio.fixture
async def redis_client() -> RedisClient:
    """Create a real Redis client for integration tests."""
    client = RedisClient()
    await client.connect()
    yield client
    # Cleanup: clear test keys
    keys = await client.scan_keys("test:*")
    if keys:
        await client.delete(*keys)
    await client.disconnect()


class TestRedisClientIntegration:
    """Integration tests for RedisClient."""

    @pytest.mark.asyncio
    async def test_ping(self, redis_client: RedisClient):
        """Test Redis connection is alive."""
        result = await redis_client.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_set_and_get(self, redis_client: RedisClient):
        """Test basic set and get operations."""
        key = "test:basic:key"
        value = "hello world"

        await redis_client.set(key, value)
        result = await redis_client.get(key)

        assert result == value

    @pytest.mark.asyncio
    async def test_set_with_expiry(self, redis_client: RedisClient):
        """Test key expiration."""
        key = "test:expiry:key"

        await redis_client.set(key, "temporary", ex=1)
        assert await redis_client.exists(key) is True

        # Wait for expiration
        await asyncio.sleep(1.5)
        assert await redis_client.exists(key) is False

    @pytest.mark.asyncio
    async def test_json_operations(self, redis_client: RedisClient):
        """Test JSON set and get."""
        key = "test:json:key"
        data = {"name": "test", "value": 123, "items": [1.0, 2.0, 3.0]}

        await redis_client.set_json(key, data)
        result = await redis_client.get_json(key)

        assert result == data

    @pytest.mark.asyncio
    async def test_delete(self, redis_client: RedisClient):
        """Test key deletion."""
        key = "test:delete:key"

        await redis_client.set(key, "to delete")
        assert await redis_client.exists(key) is True

        deleted = await redis_client.delete(key)
        assert deleted == 1
        assert await redis_client.exists(key) is False

    @pytest.mark.asyncio
    async def test_scan_keys(self, redis_client: RedisClient):
        """Test scanning keys by pattern."""
        # Create multiple keys
        for i in range(5):
            await redis_client.set(f"test:scan:{i}", str(i))

        keys = await redis_client.scan_keys("test:scan:*")

        assert len(keys) == 5
        assert all("test:scan:" in k for k in keys)


class TestEmbeddingCacheIntegration:
    """Integration tests for EmbeddingCache with real Redis."""

    @pytest_asyncio.fixture
    async def embedding_cache(self, redis_client: RedisClient) -> EmbeddingCache:
        """Create embedding cache with test prefix."""
        return EmbeddingCache(redis_client, prefix="test:embedding")

    @pytest.mark.asyncio
    async def test_cache_embedding(self, embedding_cache: EmbeddingCache):
        """Test caching and retrieving an embedding."""
        text = "Hello, world!"
        model = "test-model"
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]

        # Cache the embedding
        success = await embedding_cache.set_embedding(text, embedding, model)
        assert success is True

        # Retrieve it
        cached = await embedding_cache.get_embedding(text, model)

        assert cached is not None
        assert cached.embedding == embedding
        assert cached.model == model

    @pytest.mark.asyncio
    async def test_cache_miss(self, embedding_cache: EmbeddingCache):
        """Test cache miss returns None."""
        result = await embedding_cache.get_embedding("nonexistent", "model")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit_miss_stats(self, embedding_cache: EmbeddingCache):
        """Test hit/miss statistics are tracked."""
        embedding_cache.reset_stats()

        # Miss
        await embedding_cache.get_embedding("miss", "model")

        # Hit after set
        await embedding_cache.set_embedding("hit", [0.1], "model")
        await embedding_cache.get_embedding("hit", "model")

        stats = await embedding_cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.hit_rate == 0.5

    @pytest.mark.asyncio
    async def test_batch_operations(self, embedding_cache: EmbeddingCache):
        """Test batch get with mixed hits and misses."""
        # Set some embeddings
        await embedding_cache.set_embedding("text1", [0.1], "model")
        await embedding_cache.set_embedding("text2", [0.2], "model")

        # Batch get with one miss
        texts = ["text1", "text2", "text3"]
        results, misses = await embedding_cache.get_batch(texts, "model")

        assert len(results) == 3
        assert results[0] is not None
        assert results[1] is not None
        assert results[2] is None
        assert misses == [2]

    @pytest.mark.asyncio
    async def test_same_text_different_models(self, embedding_cache: EmbeddingCache):
        """Test that same text with different models are cached separately."""
        text = "same text"
        embedding_a = [0.1, 0.2]
        embedding_b = [0.3, 0.4]

        await embedding_cache.set_embedding(text, embedding_a, "model-a")
        await embedding_cache.set_embedding(text, embedding_b, "model-b")

        cached_a = await embedding_cache.get_embedding(text, "model-a")
        cached_b = await embedding_cache.get_embedding(text, "model-b")

        assert cached_a is not None
        assert cached_b is not None
        assert cached_a.embedding == embedding_a
        assert cached_b.embedding == embedding_b

    @pytest.mark.asyncio
    async def test_ttl_expiration(self, redis_client: RedisClient):
        """Test that embeddings expire after TTL."""
        cache = EmbeddingCache(redis_client, prefix="test:ttl", default_ttl=1)

        await cache.set_embedding("temp", [0.1], "model")
        assert await cache.get_embedding("temp", "model") is not None

        # Wait for expiration
        await asyncio.sleep(1.5)
        assert await cache.get_embedding("temp", "model") is None


class TestSessionCacheIntegration:
    """Integration tests for SessionCache with real Redis."""

    @pytest_asyncio.fixture
    async def session_cache(self, redis_client: RedisClient) -> SessionCache:
        """Create session cache with test prefix."""
        return SessionCache(redis_client, prefix="test:session", default_ttl=60)

    @pytest.mark.asyncio
    async def test_create_and_get_session(self, session_cache: SessionCache):
        """Test creating and retrieving a session."""
        session = await session_cache.create_session(
            conversation_id="conv-123",
            collection_id="coll-456",
            metadata={"user": "test"},
        )

        assert session["conversation_id"] == "conv-123"
        assert session["collection_id"] == "coll-456"
        assert session["metadata"] == {"user": "test"}
        assert session["messages"] == []

        # Retrieve it
        retrieved = await session_cache.get_session("conv-123")
        assert retrieved is not None
        assert retrieved["conversation_id"] == "conv-123"

    @pytest.mark.asyncio
    async def test_add_messages(self, session_cache: SessionCache):
        """Test adding messages to session."""
        await session_cache.create_session("conv-msg", "coll-1")

        await session_cache.add_message("conv-msg", "user", "Hello!")
        await session_cache.add_message("conv-msg", "assistant", "Hi there!")

        messages = await session_cache.get_messages("conv-msg")

        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello!"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Hi there!"

    @pytest.mark.asyncio
    async def test_max_messages_trim(self, redis_client: RedisClient):
        """Test that messages are trimmed to max_messages."""
        cache = SessionCache(redis_client, prefix="test:trim", max_messages=3)

        await cache.create_session("conv-trim", "coll-1")

        # Add 5 messages
        for i in range(5):
            await cache.add_message("conv-trim", "user", f"Message {i}")

        messages = await cache.get_messages("conv-trim")

        # Should only have last 3
        assert len(messages) == 3
        assert messages[0]["content"] == "Message 2"
        assert messages[2]["content"] == "Message 4"

    @pytest.mark.asyncio
    async def test_sliding_expiration(self, redis_client: RedisClient):
        """Test that accessing session extends TTL."""
        cache = SessionCache(redis_client, prefix="test:slide", default_ttl=2)

        await cache.create_session("conv-slide", "coll-1")

        # Access multiple times over 3 seconds (should extend TTL each time)
        for _ in range(3):
            await asyncio.sleep(0.8)
            session = await cache.get_session("conv-slide")
            assert session is not None

        # Session should still exist (TTL extended)
        assert await cache.session_exists("conv-slide") is True

    @pytest.mark.asyncio
    async def test_delete_session(self, session_cache: SessionCache):
        """Test deleting a session."""
        await session_cache.create_session("conv-del", "coll-1")
        assert await session_cache.session_exists("conv-del") is True

        await session_cache.delete_session("conv-del")
        assert await session_cache.session_exists("conv-del") is False


class TestRateLimiterIntegration:
    """Integration tests for RateLimiter with real Redis.

    These tests validate the Lua script actually works correctly.
    """

    @pytest_asyncio.fixture
    async def rate_limiter(self, redis_client: RedisClient) -> RateLimiter:
        """Create rate limiter with test prefix."""
        return RateLimiter(
            redis_client,
            prefix="test:ratelimit",
            default_limit=5,
            default_window=10,
        )

    @pytest.mark.asyncio
    async def test_acquire_under_limit(self, rate_limiter: RateLimiter):
        """Test acquiring slots under the limit."""
        identifier = f"user-{time.time()}"

        for i in range(5):
            info = await rate_limiter.acquire(identifier)
            assert info.allowed is True
            assert info.remaining == 5 - (i + 1)

    @pytest.mark.asyncio
    async def test_acquire_exceeds_limit(self, rate_limiter: RateLimiter):
        """Test that exceeding limit raises exception."""
        identifier = f"user-exceed-{time.time()}"

        # Use all 5 slots
        for _ in range(5):
            await rate_limiter.acquire(identifier)

        # 6th should fail
        with pytest.raises(RateLimitExceeded) as exc_info:
            await rate_limiter.acquire(identifier)

        assert exc_info.value.limit == 5
        assert exc_info.value.retry_after > 0

    @pytest.mark.asyncio
    async def test_check_without_incrementing(self, rate_limiter: RateLimiter):
        """Test checking limit without consuming a slot."""
        identifier = f"user-check-{time.time()}"

        # Check multiple times - should not increment
        for _ in range(10):
            info = await rate_limiter.check(identifier)
            assert info.allowed is True
            assert info.remaining == 5

    @pytest.mark.asyncio
    async def test_sliding_window_expiration(self, redis_client: RedisClient):
        """Test that requests expire from sliding window."""
        limiter = RateLimiter(
            redis_client,
            prefix="test:slide",
            default_limit=2,
            default_window=2,
        )
        identifier = f"user-window-{time.time()}"

        # Use both slots
        await limiter.acquire(identifier)
        await limiter.acquire(identifier)

        # Should be at limit
        info = await limiter.check(identifier)
        assert info.allowed is False

        # Wait for window to expire
        await asyncio.sleep(2.5)

        # Should be allowed again
        info = await limiter.check(identifier)
        assert info.allowed is True

    @pytest.mark.asyncio
    async def test_acquire_with_cost(self, rate_limiter: RateLimiter):
        """Test acquiring multiple slots at once."""
        identifier = f"user-cost-{time.time()}"

        # Acquire 3 slots at once
        info = await rate_limiter.acquire(identifier, cost=3)
        assert info.allowed is True
        assert info.remaining == 2

        # Acquire 2 more
        info = await rate_limiter.acquire(identifier, cost=2)
        assert info.allowed is True
        assert info.remaining == 0

        # 1 more should fail
        with pytest.raises(RateLimitExceeded):
            await rate_limiter.acquire(identifier, cost=1)

    @pytest.mark.asyncio
    async def test_reset_clears_limit(self, rate_limiter: RateLimiter):
        """Test resetting clears the rate limit."""
        identifier = f"user-reset-{time.time()}"

        # Use all slots
        for _ in range(5):
            await rate_limiter.acquire(identifier)

        # Reset
        await rate_limiter.reset(identifier)

        # Should be able to acquire again
        info = await rate_limiter.acquire(identifier)
        assert info.allowed is True
        assert info.remaining == 4

    @pytest.mark.asyncio
    async def test_different_resources(self, rate_limiter: RateLimiter):
        """Test that different resources have separate limits."""
        identifier = f"user-res-{time.time()}"

        # Use all slots on resource A
        for _ in range(5):
            await rate_limiter.acquire(identifier, resource="chat")

        # Resource B should still have slots
        info = await rate_limiter.check(identifier, resource="embed")
        assert info.allowed is True
        assert info.remaining == 5

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, rate_limiter: RateLimiter):
        """Test that concurrent requests are handled atomically."""
        identifier = f"user-concurrent-{int(time.time() * 1000000)}"
        limit = 5

        # Clean state before test
        await rate_limiter.reset(identifier)

        # Send 10 concurrent requests with limit of 5
        tasks = [rate_limiter.acquire(identifier, limit=limit, window=60) for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Separate successes and failures by type
        successes = []
        failures = []

        for result in results:
            if isinstance(result, RateLimitExceeded):
                failures.append(result)
            elif isinstance(result, Exception):
                # Unexpected exception - should not happen
                raise AssertionError(f"Unexpected exception: {result}")
            else:
                # Should be RateLimitInfo object with allowed=True
                assert hasattr(result, 'allowed'), f"Expected RateLimitInfo, got {type(result)}"
                assert result.allowed is True, "Successful result should have allowed=True"
                successes.append(result)

        # Exactly 5 should succeed, 5 should fail with RateLimitExceeded
        assert len(successes) == limit, f"Expected {limit} successes, got {len(successes)}"
        assert len(failures) == (10 - limit), f"Expected {10 - limit} failures, got {len(failures)}"

        # Verify all failures are RateLimitExceeded with correct limits
        for failure in failures:
            assert isinstance(failure, RateLimitExceeded)
            assert failure.limit == limit
            assert failure.retry_after > 0

    @pytest.mark.asyncio
    async def test_get_usage(self, rate_limiter: RateLimiter):
        """Test getting current usage count."""
        identifier = f"user-usage-{time.time()}"

        await rate_limiter.acquire(identifier)
        await rate_limiter.acquire(identifier)
        await rate_limiter.acquire(identifier)

        usage = await rate_limiter.get_usage(identifier)
        assert usage == 3
