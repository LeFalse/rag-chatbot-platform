"""Session cache for conversation context."""

import json
import logging
from datetime import datetime
from typing import Literal

from app.services.cache.base import BaseCache
from app.services.cache.redis_client import RedisClient
from app.services.cache.types import CacheStats, MessageData, SessionData

logger = logging.getLogger(__name__)

# 1 hour default session TTL
DEFAULT_SESSION_TTL = 3600


class SessionCache(BaseCache):
    """Cache for conversation session data.

    Stores conversation messages and context in Redis
    for quick retrieval during chat interactions.
    Extends session TTL on each access (sliding expiration).

    Key format: session:{conversation_id}
    TTL: 1 hour (sliding)
    """

    def __init__(
        self,
        redis_client: RedisClient,
        prefix: str = "session",
        default_ttl: int = DEFAULT_SESSION_TTL,
        max_messages: int = 50,
    ):
        """Initialize session cache.

        Args:
            redis_client: Redis client instance.
            prefix: Key prefix for session entries.
            default_ttl: Default TTL in seconds (1h default).
            max_messages: Maximum messages to store per session.
        """
        self.redis = redis_client
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.max_messages = max_messages
        self._hits = 0
        self._misses = 0

    def _make_key(self, conversation_id: str) -> str:
        """Generate cache key for conversation.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            Cache key string.
        """
        return f"{self.prefix}:{conversation_id}"

    async def get(self, key: str) -> SessionData | None:
        """Retrieve session data by key.

        Extends TTL on access (sliding expiration).

        Args:
            key: Cache key.

        Returns:
            SessionData or None if not found.
        """
        data = await self.redis.get(key)
        if data is None:
            self._misses += 1
            return None

        self._hits += 1
        # Extend TTL on access (sliding expiration)
        await self.redis.expire(key, self.default_ttl)

        try:
            parsed = json.loads(data)
            return SessionData(
                conversation_id=parsed.get("conversation_id", ""),
                collection_id=parsed.get("collection_id", ""),
                messages=parsed.get("messages", []),
                created_at=parsed.get("created_at", ""),
                last_activity=parsed.get("last_activity", ""),
                metadata=parsed.get("metadata", {}),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse session data: {e}")
            return None

    async def get_session(self, conversation_id: str) -> SessionData | None:
        """Get session by conversation ID.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            SessionData or None.
        """
        key = self._make_key(conversation_id)
        return await self.get(key)

    async def set(
        self,
        key: str,
        value: SessionData,
        ttl: int | None = None,
    ) -> bool:
        """Store session data.

        Args:
            key: Cache key.
            value: SessionData to store.
            ttl: TTL in seconds.

        Returns:
            True if stored successfully.
        """
        expiry = ttl if ttl is not None else self.default_ttl
        data = json.dumps(value)
        return await self.redis.set(key, data, ex=expiry)

    async def create_session(
        self,
        conversation_id: str,
        collection_id: str,
        metadata: dict[str, str] | None = None,
    ) -> SessionData:
        """Create a new session.

        Args:
            conversation_id: Conversation UUID.
            collection_id: Associated collection UUID.
            metadata: Optional session metadata.

        Returns:
            Created SessionData.
        """
        now = datetime.utcnow().isoformat()
        session = SessionData(
            conversation_id=conversation_id,
            collection_id=collection_id,
            messages=[],
            created_at=now,
            last_activity=now,
            metadata=metadata or {},
        )

        key = self._make_key(conversation_id)
        await self.set(key, session)
        return session

    async def add_message(
        self,
        conversation_id: str,
        role: Literal["system", "user", "assistant"],
        content: str,
    ) -> bool:
        """Add a message to session.

        Maintains max_messages limit by removing oldest messages.

        Args:
            conversation_id: Conversation UUID.
            role: Message role.
            content: Message content.

        Returns:
            True if message was added.
        """
        session = await self.get_session(conversation_id)
        if session is None:
            logger.warning(f"Session not found: {conversation_id}")
            return False

        message = MessageData(
            role=role,
            content=content,
            timestamp=datetime.utcnow().isoformat(),
        )

        # Add new message
        messages = session["messages"]
        messages.append(message)

        # Trim to max_messages (keep newest)
        if len(messages) > self.max_messages:
            messages = messages[-self.max_messages :]

        # Update session
        session["messages"] = messages
        session["last_activity"] = datetime.utcnow().isoformat()

        key = self._make_key(conversation_id)
        return await self.set(key, session)

    async def get_messages(
        self,
        conversation_id: str,
        limit: int | None = None,
    ) -> list[MessageData]:
        """Get messages from session.

        Args:
            conversation_id: Conversation UUID.
            limit: Max messages to return (newest first).

        Returns:
            List of messages.
        """
        session = await self.get_session(conversation_id)
        if session is None:
            return []

        messages = session["messages"]
        if limit is not None:
            return messages[-limit:]
        return messages

    async def get_context_window(
        self,
        conversation_id: str,
        max_tokens: int = 4000,
        avg_tokens_per_message: int = 100,
    ) -> list[MessageData]:
        """Get messages that fit within token limit.

        Estimates tokens based on message count.
        Returns newest messages that fit.

        Args:
            conversation_id: Conversation UUID.
            max_tokens: Maximum tokens to return.
            avg_tokens_per_message: Estimated tokens per message.

        Returns:
            List of messages within token budget.
        """
        max_messages = max_tokens // avg_tokens_per_message
        return await self.get_messages(conversation_id, limit=max_messages)

    async def update_metadata(
        self,
        conversation_id: str,
        metadata: dict[str, str],
    ) -> bool:
        """Update session metadata.

        Args:
            conversation_id: Conversation UUID.
            metadata: Metadata to merge.

        Returns:
            True if updated.
        """
        session = await self.get_session(conversation_id)
        if session is None:
            return False

        session["metadata"].update(metadata)
        session["last_activity"] = datetime.utcnow().isoformat()

        key = self._make_key(conversation_id)
        return await self.set(key, session)

    async def delete(self, key: str) -> bool:
        """Delete session.

        Args:
            key: Cache key.

        Returns:
            True if deleted.
        """
        result = await self.redis.delete(key)
        return result > 0

    async def delete_session(self, conversation_id: str) -> bool:
        """Delete session by conversation ID.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            True if deleted.
        """
        key = self._make_key(conversation_id)
        return await self.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if session exists.

        Args:
            key: Cache key.

        Returns:
            True if exists.
        """
        return await self.redis.exists(key)

    async def session_exists(self, conversation_id: str) -> bool:
        """Check if session exists by conversation ID.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            True if exists.
        """
        key = self._make_key(conversation_id)
        return await self.exists(key)

    async def clear(self, pattern: str | None = None) -> int:
        """Clear session cache.

        Args:
            pattern: Optional pattern. Defaults to all sessions.

        Returns:
            Number of sessions deleted.
        """
        search_pattern = pattern or f"{self.prefix}:*"
        keys = await self.redis.scan_keys(search_pattern)
        if not keys:
            return 0
        return await self.redis.delete(*keys)

    async def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            CacheStats with hits, misses, and size.
        """
        keys = await self.redis.scan_keys(f"{self.prefix}:*")
        return CacheStats(
            hits=self._hits,
            misses=self._misses,
            size=len(keys),
        )

    def reset_stats(self) -> None:
        """Reset hit/miss counters."""
        self._hits = 0
        self._misses = 0
