"""Base cache interface."""

from abc import ABC, abstractmethod
from typing import TypeVar

from app.services.cache.types import CacheStats

T = TypeVar("T")


class BaseCache(ABC):
    """Abstract base class for cache implementations.

    Follows the Strategy pattern to allow different cache backends.
    All implementations must be async-compatible.
    """

    @abstractmethod
    async def get(self, key: str) -> T | None:
        """Retrieve a value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found.
        """

    @abstractmethod
    async def set(self, key: str, value: T, ttl: int | None = None) -> bool:
        """Store a value in cache.

        Args:
            key: Cache key.
            value: Value to store.
            ttl: Time to live in seconds. None for no expiration.

        Returns:
            True if stored successfully.
        """

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Remove a value from cache.

        Args:
            key: Cache key.

        Returns:
            True if deleted, False if key didn't exist.
        """

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache.

        Args:
            key: Cache key.

        Returns:
            True if key exists.
        """

    @abstractmethod
    async def clear(self, pattern: str | None = None) -> int:
        """Clear cache entries.

        Args:
            pattern: Optional pattern to match keys (e.g., "embedding:*").
                    If None, clears all keys in the cache namespace.

        Returns:
            Number of keys deleted.
        """

    @abstractmethod
    async def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            CacheStats with hits, misses, and size.
        """
