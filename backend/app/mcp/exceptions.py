"""MCP client exceptions."""


class MCPError(Exception):
    """Base exception for MCP client errors."""

    def __init__(self, message: str, details: dict[str, object] | None = None):
        """Initialize MCP error.

        Args:
            message: Error message.
            details: Additional error details.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class MCPConnectionError(MCPError):
    """Error connecting to MCP server."""

    def __init__(self, message: str, command: list[str] | None = None):
        """Initialize connection error.

        Args:
            message: Error message.
            command: Command that was attempted.
        """
        super().__init__(message, {"command": command})
        self.command = command


class MCPTimeoutError(MCPError):
    """Timeout waiting for MCP server response."""

    def __init__(self, message: str, timeout: float):
        """Initialize timeout error.

        Args:
            message: Error message.
            timeout: Timeout value in seconds.
        """
        super().__init__(message, {"timeout": timeout})
        self.timeout = timeout


class MCPProtocolError(MCPError):
    """Invalid JSON-RPC protocol response."""

    def __init__(self, message: str, response: dict[str, object] | None = None):
        """Initialize protocol error.

        Args:
            message: Error message.
            response: Invalid response received.
        """
        super().__init__(message, {"response": response})
        self.response = response


class MCPToolError(MCPError):
    """Error executing MCP tool."""

    def __init__(self, message: str, tool_name: str, error_content: str | None = None):
        """Initialize tool error.

        Args:
            message: Error message.
            tool_name: Name of the tool that failed.
            error_content: Error content from tool.
        """
        super().__init__(message, {"tool_name": tool_name, "error_content": error_content})
        self.tool_name = tool_name
        self.error_content = error_content
