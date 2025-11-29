"""Type definitions for embedding providers."""

from dataclasses import dataclass


@dataclass
class EmbeddingResult:
    """Result from an embedding provider."""

    embedding: list[float]
    model: str
    tokens_used: int


@dataclass
class EmbeddingConfig:
    """Configuration for embedding providers."""

    model: str
    dimension: int = 1536  # Default for OpenAI text-embedding-3-small


@dataclass
class BatchEmbeddingResult:
    """Result from batch embedding operation."""

    embeddings: list[list[float]]
    model: str
    total_tokens: int
