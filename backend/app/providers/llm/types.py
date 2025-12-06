"""Type definitions for LLM providers."""

from dataclasses import dataclass, field
from typing import Literal, TypedDict


class ChatMessage(TypedDict):
    """A single message in a chat conversation."""

    role: Literal["system", "user", "assistant"]
    content: str


# Tool Calling Types
class ToolParameter(TypedDict, total=False):
    """JSON Schema definition for a tool parameter."""

    type: str
    description: str
    enum: list[str]
    items: dict[str, str]


class ToolParameters(TypedDict):
    """JSON Schema for tool parameters."""

    type: Literal["object"]
    properties: dict[str, ToolParameter]
    required: list[str]


class ToolFunction(TypedDict):
    """Function definition for a tool."""

    name: str
    description: str
    parameters: ToolParameters


class ToolDefinition(TypedDict):
    """Complete tool definition for LLM."""

    type: Literal["function"]
    function: ToolFunction


@dataclass
class ToolCall:
    """A tool call requested by the LLM."""

    id: str
    name: str
    arguments: dict[str, str | int | float | bool | list[str] | None]


class ToolMessage(TypedDict):
    """Message containing tool call result."""

    role: Literal["tool"]
    tool_call_id: str
    content: str


class AssistantMessageWithToolCalls(TypedDict):
    """Assistant message that includes tool calls."""

    role: Literal["assistant"]
    content: str | None
    tool_calls: list[dict[str, str | dict[str, str]]]


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
    temperature: float = 0.5  # Balanced temperature for natural varied responses
    max_tokens: int = 512  # Reduced for concise RAG responses
    top_p: float = 1.0
    context_window: int = 4096  # Context window size (num_ctx for Ollama)
    context_window_tools: int = 8192  # Larger context for tool calling workflows
    stop_sequences: list[str] = field(default_factory=list)


@dataclass
class StreamChunk:
    """A chunk of streamed response."""

    content: str
    is_final: bool = False
    finish_reason: str | None = None
    tokens_input: int | None = None
    tokens_output: int | None = None


@dataclass
class LLMResponseWithTools:
    """Response from LLM that may contain tool calls.

    Used for agent workflows where the LLM can request tool execution.
    """

    content: str | None
    tool_calls: list[ToolCall] | None
    model: str
    tokens_input: int
    tokens_output: int
    finish_reason: str | None = None

    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return bool(self.tool_calls)

    @property
    def is_final_response(self) -> bool:
        """Check if this is a final response (no tool calls)."""
        return self.content is not None and not self.has_tool_calls
