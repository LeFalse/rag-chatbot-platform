"""Redis async client configuration."""

import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client wrapper.

    Provides connection pooling and helper methods for
    common Redis operations. Uses redis-py async interface.
    """

    def __init__(
        self,
        url: str | None = None,
        max_connections: int = 10,
        decode_responses: bool = True,
    ):
        """Initialize Redis client.

        Args:
            url: Redis connection URL. Defaults to settings.redis_url.
            max_connections: Maximum connections in pool.
            decode_responses: Whether to decode bytes to strings.
        """
        settings = get_settings()
        self.url = url or settings.redis_url
        self.max_connections = max_connections
        self.decode_responses = decode_responses
        self._pool: redis.ConnectionPool | None = None
        self._client: Redis | None = None

    async def connect(self) -> None:
        """Establish connection pool to Redis."""
        if self._pool is not None:
            return

        self._pool = redis.ConnectionPool.from_url(
            self.url,
            max_connections=self.max_connections,
            decode_responses=self.decode_responses,
        )
        self._client = Redis(connection_pool=self._pool)
        logger.info("Redis connection pool established")

    async def disconnect(self) -> None:
        """Close Redis connection pool."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        logger.info("Redis connection pool closed")

    @property
    def client(self) -> Redis:
        """Get Redis client instance.

        Returns:
            Redis client.

        Raises:
            RuntimeError: If not connected.
        """
        if self._client is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    async def ping(self) -> bool:
        """Check Redis connection health.

        Returns:
            True if Redis is responding.
        """
        try:
            result = await self.client.ping()
            return result is True or result == "PONG"
        except Exception as e:
            logger.warning(f"Redis ping failed: {e}")
            return False

    async def get(self, key: str) -> str | None:
        """Get a string value from Redis.

        Args:
            key: Redis key.

        Returns:
            Value or None if not found.
        """
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        ex: int | None = None,
    ) -> bool:
        """Set a string value in Redis.

        Args:
            key: Redis key.
            value: Value to store.
            ex: Expiration in seconds.

        Returns:
            True if set successfully.
        """
        result = await self.client.set(key, value, ex=ex)
        return result is True

    async def get_json(self, key: str) -> dict[str, str | int | float | list[float]] | None:
        """Get and parse a JSON value from Redis.

        Args:
            key: Redis key.

        Returns:
            Parsed dict or None if not found.
        """
        data = await self.get(key)
        if data is None:
            return None
        try:
            result = json.loads(data)
            if isinstance(result, dict):
                return result
            return None
        except json.JSONDecodeError:
            logger.warning(f"Failed to decode JSON for key: {key}")
            return None

    async def set_json(
        self,
        key: str,
        value: dict[str, str | int | float | list[float]],
        ex: int | None = None,
    ) -> bool:
        """Store a value as JSON in Redis.

        Args:
            key: Redis key.
            value: Dict to store.
            ex: Expiration in seconds.

        Returns:
            True if set successfully.
        """
        return await self.set(key, json.dumps(value), ex=ex)

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys.

        Args:
            keys: Keys to delete.

        Returns:
            Number of keys deleted.
        """
        if not keys:
            return 0
        return await self.client.delete(*keys)

    async def exists(self, key: str) -> bool:
        """Check if a key exists.

        Args:
            key: Redis key.

        Returns:
            True if key exists.
        """
        result = await self.client.exists(key)
        return result > 0

    async def keys(self, pattern: str) -> list[str]:
        """Get keys matching pattern.

        Warning: Use with caution in production.
        Consider SCAN for large datasets.

        Args:
            pattern: Key pattern (e.g., "embedding:*").

        Returns:
            List of matching keys.
        """
        return await self.client.keys(pattern)

    async def scan_keys(self, pattern: str, count: int = 100) -> list[str]:
        """Scan keys matching pattern (production-safe).

        Uses SCAN command which doesn't block Redis.

        Args:
            pattern: Key pattern.
            count: Hint for batch size.

        Returns:
            List of matching keys.
        """
        keys: list[str] = []
        cursor = 0
        while True:
            cursor, batch = await self.client.scan(
                cursor=cursor,
                match=pattern,
                count=count,
            )
            keys.extend(batch)
            if cursor == 0:
                break
        return keys

    async def incr(self, key: str) -> int:
        """Increment a key's integer value.

        Args:
            key: Redis key.

        Returns:
            New value after increment.
        """
        return await self.client.incr(key)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set key expiration.

        Args:
            key: Redis key.
            seconds: Seconds until expiration.

        Returns:
            True if timeout was set.
        """
        return await self.client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """Get remaining time to live for a key.

        Args:
            key: Redis key.

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist.
        """
        return await self.client.ttl(key)


# Global client instance
_redis_client: RedisClient | None = None


async def get_redis_client() -> RedisClient:
    """Get or create the global Redis client.

    Returns:
        Connected RedisClient instance.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()
    return _redis_client


@asynccontextmanager
async def redis_context() -> AsyncGenerator[RedisClient, None]:
    """Context manager for Redis client lifecycle.

    Usage:
        async with redis_context() as client:
            await client.set("key", "value")
    """
    client = RedisClient()
    await client.connect()
    try:
        yield client
    finally:
        await client.disconnect()
