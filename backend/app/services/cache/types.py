"""Cache types and data structures."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, TypedDict


class MessageData(TypedDict):
    """Structure for cached message data."""

    role: Literal["system", "user", "assistant"]
    content: str
    timestamp: str


class SessionData(TypedDict):
    """Structure for cached session/conversation data."""

    conversation_id: str
    collection_id: str
    messages: list[MessageData]
    created_at: str
    last_activity: str
    metadata: dict[str, str]


@dataclass
class CachedEmbedding:
    """Cached embedding result."""

    embedding: list[float]
    model: str
    cached_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, str | list[float]]:
        """Convert to dictionary for Redis storage."""
        return {
            "embedding": self.embedding,
            "model": self.model,
            "cached_at": self.cached_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, str | list[float]]) -> "CachedEmbedding":
        """Create from dictionary (Redis retrieval)."""
        cached_at_str = data.get("cached_at", "")
        if isinstance(cached_at_str, str) and cached_at_str:
            cached_at = datetime.fromisoformat(cached_at_str)
        else:
            cached_at = datetime.utcnow()

        embedding = data.get("embedding", [])
        model = data.get("model", "")

        return cls(
            embedding=embedding if isinstance(embedding, list) else [],
            model=model if isinstance(model, str) else "",
            cached_at=cached_at,
        )


@dataclass
class CacheStats:
    """Cache statistics."""

    hits: int = 0
    misses: int = 0
    size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total


@dataclass
class RateLimitInfo:
    """Rate limit status information."""

    allowed: bool
    remaining: int
    limit: int
    reset_at: datetime
    retry_after: float | None = None

    @property
    def is_limited(self) -> bool:
        """Check if rate limit is exceeded."""
        return not self.allowed
