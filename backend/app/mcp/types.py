"""Type definitions for MCP client."""

from dataclasses import dataclass, field
from typing import Literal, TypedDict


class MCPToolParameter(TypedDict, total=False):
    """JSON Schema definition for a tool parameter."""

    type: str
    description: str
    enum: list[str]
    items: dict[str, str]
    default: str | int | float | bool | None


class MCPToolInputSchema(TypedDict):
    """JSON Schema for tool input."""

    type: Literal["object"]
    properties: dict[str, MCPToolParameter]
    required: list[str]


@dataclass
class MCPTool:
    """Tool definition from MCP server."""

    name: str
    description: str
    input_schema: MCPToolInputSchema

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "MCPTool":
        """Create MCPTool from dictionary.

        Args:
            data: Tool data from MCP server.

        Returns:
            MCPTool instance.
        """
        return cls(
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            input_schema=data.get("inputSchema", {
                "type": "object",
                "properties": {},
                "required": [],
            }),
        )


@dataclass
class MCPToolResult:
    """Result from calling an MCP tool."""

    content: list[dict[str, str]]
    is_error: bool = False

    @property
    def text(self) -> str:
        """Get concatenated text content."""
        return "\n".join(
            item.get("text", "")
            for item in self.content
            if item.get("type") == "text"
        )

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "MCPToolResult":
        """Create MCPToolResult from dictionary.

        Args:
            data: Result data from MCP server.

        Returns:
            MCPToolResult instance.
        """
        return cls(
            content=data.get("content", []),
            is_error=bool(data.get("isError", False)),
        )


@dataclass
class MCPServerInfo:
    """Information about connected MCP server."""

    name: str
    version: str
    protocol_version: str = "2024-11-05"


# JSON-RPC 2.0 Types
class JSONRPCRequest(TypedDict):
    """JSON-RPC 2.0 request."""

    jsonrpc: Literal["2.0"]
    id: int | str
    method: str
    params: dict[str, object] | None


class JSONRPCResponse(TypedDict, total=False):
    """JSON-RPC 2.0 response."""

    jsonrpc: Literal["2.0"]
    id: int | str | None
    result: dict[str, object]
    error: dict[str, object]


class JSONRPCNotification(TypedDict):
    """JSON-RPC 2.0 notification (no id)."""

    jsonrpc: Literal["2.0"]
    method: str
    params: dict[str, object] | None
