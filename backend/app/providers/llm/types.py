"""Type definitions for LLM providers."""

from dataclasses import dataclass, field
from typing import Literal, TypedDict


class ChatMessage(TypedDict):
    """A single message in a chat conversation."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    model: str
    tokens_input: int
    tokens_output: int
    finish_reason: str | None = None


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""

    model: str
    temperature: float = 0.3  # Low temperature for consistent but slightly varied responses
    max_tokens: int = 512  # Reduced for concise RAG responses
    top_p: float = 1.0
    stop_sequences: list[str] = field(default_factory=list)


@dataclass
class StreamChunk:
    """A chunk of streamed response."""

    content: str
    is_final: bool = False
    finish_reason: str | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None
