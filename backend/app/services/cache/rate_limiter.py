"""Rate limiter using Redis sliding window algorithm."""

import logging
import time
import uuid
from datetime import datetime

from app.services.cache.redis_client import RedisClient
from app.services.cache.types import RateLimitInfo

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        limit: int,
        window: int,
        retry_after: float,
    ):
        """Initialize exception.

        Args:
            limit: Request limit.
            window: Window size in seconds.
            retry_after: Seconds until next request allowed.
        """
        self.limit = limit
        self.window = window
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window}s. "
            f"Retry after {retry_after:.1f}s"
        )


class RateLimiter:
    """Rate limiter using Redis sliding window log algorithm.

    The sliding window log algorithm tracks exact timestamps of
    requests within the window. More accurate than fixed windows
    but uses more memory.

    Provides smooth rate limiting without bursts at window edges.

    Key format: ratelimit:{identifier}
    Uses Redis sorted sets (ZSET) for efficient window queries.
    """

    def __init__(
        self,
        redis_client: RedisClient,
        prefix: str = "ratelimit",
        default_limit: int = 60,
        default_window: int = 60,
    ):
        """Initialize rate limiter.

        Args:
            redis_client: Redis client instance.
            prefix: Key prefix for rate limit entries.
            default_limit: Default requests per window.
            default_window: Default window size in seconds.
        """
        self.redis = redis_client
        self.prefix = prefix
        self.default_limit = default_limit
        self.default_window = default_window

    def _make_key(self, identifier: str, resource: str = "default") -> str:
        """Generate cache key for rate limit.

        Args:
            identifier: User/IP identifier.
            resource: Resource being limited (e.g., "chat", "embed").

        Returns:
            Cache key string.
        """
        return f"{self.prefix}:{resource}:{identifier}"

    async def check(
        self,
        identifier: str,
        resource: str = "default",
        limit: int | None = None,
        window: int | None = None,
    ) -> RateLimitInfo:
        """Check rate limit without incrementing.

        Args:
            identifier: User/IP identifier.
            resource: Resource being limited.
            limit: Request limit (uses default if None).
            window: Window size in seconds.

        Returns:
            RateLimitInfo with current status.
        """
        limit = limit or self.default_limit
        window = window or self.default_window

        key = self._make_key(identifier, resource)
        now = time.time()
        window_start = now - window

        # Remove expired entries and count current
        client = self.redis.client
        await client.zremrangebyscore(key, 0, window_start)
        count = await client.zcard(key)

        remaining = max(0, limit - count)
        reset_at = datetime.fromtimestamp(now + window)

        return RateLimitInfo(
            allowed=count < limit,
            remaining=remaining,
            limit=limit,
            reset_at=reset_at,
            retry_after=window if count >= limit else None,
        )

    async def acquire(
        self,
        identifier: str,
        resource: str = "default",
        limit: int | None = None,
        window: int | None = None,
        cost: int = 1,
    ) -> RateLimitInfo:
        """Acquire rate limit slot (increment counter).

        Uses atomic Lua script for consistency.

        Args:
            identifier: User/IP identifier.
            resource: Resource being limited.
            limit: Request limit.
            window: Window size in seconds.
            cost: Number of slots to consume (for weighted limiting).

        Returns:
            RateLimitInfo with updated status.

        Raises:
            RateLimitExceeded: If limit is exceeded.
        """
        limit = limit or self.default_limit
        window = window or self.default_window

        key = self._make_key(identifier, resource)
        now = time.time()
        window_start = now - window

        # Lua script for atomic rate limiting
        # 1. Remove expired entries
        # 2. Count current entries
        # 3. If under limit, add new entry
        # 4. Return count
        lua_script = """
        local key = KEYS[1]
        local window_start = tonumber(ARGV[1])
        local now = tonumber(ARGV[2])
        local limit = tonumber(ARGV[3])
        local cost = tonumber(ARGV[4])
        local window = tonumber(ARGV[5])
        local unique_id = ARGV[6]

        -- Remove expired entries
        redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

        -- Get current count
        local count = redis.call('ZCARD', key)

        -- Check if under limit
        if count + cost <= limit then
            -- Add entries for cost with unique identifier to avoid collisions
            for i = 1, cost do
                redis.call('ZADD', key, now, unique_id .. ':' .. i)
            end
            -- Set expiry
            redis.call('EXPIRE', key, window + 1)
            return {1, count + cost}
        else
            return {0, count}
        end
        """

        client = self.redis.client
        unique_id = str(uuid.uuid4())
        result = await client.eval(
            lua_script,
            1,
            key,
            str(window_start),
            str(now),
            str(limit),
            str(cost),
            str(window),
            unique_id,
        )

        allowed = result[0] == 1
        count = result[1]
        remaining = max(0, limit - count)
        reset_at = datetime.fromtimestamp(now + window)

        if not allowed:
            # Calculate when oldest entry expires
            oldest = await client.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_time = oldest[0][1]
                retry_after = (oldest_time + window) - now
            else:
                retry_after = float(window)

            info = RateLimitInfo(
                allowed=False,
                remaining=0,
                limit=limit,
                reset_at=reset_at,
                retry_after=retry_after,
            )
            raise RateLimitExceeded(limit, window, retry_after)

        return RateLimitInfo(
            allowed=True,
            remaining=remaining,
            limit=limit,
            reset_at=reset_at,
        )

    async def reset(
        self,
        identifier: str,
        resource: str = "default",
    ) -> bool:
        """Reset rate limit for identifier.

        Args:
            identifier: User/IP identifier.
            resource: Resource to reset.

        Returns:
            True if reset.
        """
        key = self._make_key(identifier, resource)
        result = await self.redis.delete(key)
        return result > 0

    async def get_usage(
        self,
        identifier: str,
        resource: str = "default",
        window: int | None = None,
    ) -> int:
        """Get current usage count.

        Args:
            identifier: User/IP identifier.
            resource: Resource to check.
            window: Window size in seconds.

        Returns:
            Current request count in window.
        """
        window = window or self.default_window
        key = self._make_key(identifier, resource)
        now = time.time()
        window_start = now - window

        client = self.redis.client
        await client.zremrangebyscore(key, 0, window_start)
        return await client.zcard(key)


class MultiResourceRateLimiter:
    """Rate limiter with multiple resource limits.

    Allows defining different limits for different resources
    (e.g., stricter limits for expensive operations).
    """

    def __init__(
        self,
        redis_client: RedisClient,
        limits: dict[str, tuple[int, int]],
    ):
        """Initialize multi-resource limiter.

        Args:
            redis_client: Redis client instance.
            limits: Dict of resource -> (limit, window) tuples.
                   Example: {"chat": (60, 60), "embed": (100, 60)}
        """
        self._limiter = RateLimiter(redis_client)
        self._limits = limits

    async def acquire(
        self,
        identifier: str,
        resource: str,
    ) -> RateLimitInfo:
        """Acquire rate limit for specific resource.

        Args:
            identifier: User/IP identifier.
            resource: Resource to limit.

        Returns:
            RateLimitInfo.

        Raises:
            RateLimitExceeded: If limit exceeded.
            ValueError: If resource not configured.
        """
        if resource not in self._limits:
            raise ValueError(f"Unknown resource: {resource}")

        limit, window = self._limits[resource]
        return await self._limiter.acquire(
            identifier,
            resource=resource,
            limit=limit,
            window=window,
        )

    async def check(
        self,
        identifier: str,
        resource: str,
    ) -> RateLimitInfo:
        """Check rate limit for specific resource.

        Args:
            identifier: User/IP identifier.
            resource: Resource to check.

        Returns:
            RateLimitInfo.

        Raises:
            ValueError: If resource not configured.
        """
        if resource not in self._limits:
            raise ValueError(f"Unknown resource: {resource}")

        limit, window = self._limits[resource]
        return await self._limiter.check(
            identifier,
            resource=resource,
            limit=limit,
            window=window,
        )
