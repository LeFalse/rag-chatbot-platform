"""Tests for MCP exceptions."""

import pytest

from app.mcp.exceptions import (
    MCPConnectionError,
    MCPError,
    MCPProtocolError,
    MCPTimeoutError,
    MCPToolError,
)


class TestMCPError:
    """Tests for base MCPError."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = MCPError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.details == {}

    def test_error_with_details(self):
        """Test error with additional details."""
        error = MCPError(
            "Something went wrong",
            details={"code": 500, "context": "during initialization"},
        )

        assert error.details == {"code": 500, "context": "during initialization"}


class TestMCPConnectionError:
    """Tests for MCPConnectionError."""

    def test_connection_error_with_command(self):
        """Test connection error stores command."""
        error = MCPConnectionError(
            "Failed to start server",
            command=["npx", "-y", "@anthropic/server"],
        )

        assert error.command == ["npx", "-y", "@anthropic/server"]
        assert error.details["command"] == ["npx", "-y", "@anthropic/server"]

    def test_connection_error_without_command(self):
        """Test connection error without command."""
        error = MCPConnectionError("Not connected")

        assert error.command is None
        assert error.details["command"] is None


class TestMCPTimeoutError:
    """Tests for MCPTimeoutError."""

    def test_timeout_error_stores_value(self):
        """Test timeout error stores timeout value."""
        error = MCPTimeoutError("Request timed out", timeout=30.0)

        assert error.timeout == 30.0
        assert error.details["timeout"] == 30.0

    def test_timeout_error_message(self):
        """Test timeout error message."""
        error = MCPTimeoutError("Operation timed out after 30s", timeout=30.0)

        assert "30" in str(error)


class TestMCPProtocolError:
    """Tests for MCPProtocolError."""

    def test_protocol_error_with_response(self):
        """Test protocol error stores response."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32600, "message": "Invalid Request"},
        }
        error = MCPProtocolError("Invalid JSON-RPC response", response=response)

        assert error.response == response
        assert error.details["response"] == response

    def test_protocol_error_without_response(self):
        """Test protocol error without response."""
        error = MCPProtocolError("Malformed JSON")

        assert error.response is None


class TestMCPToolError:
    """Tests for MCPToolError."""

    def test_tool_error_with_all_fields(self):
        """Test tool error with all fields."""
        error = MCPToolError(
            "Tool execution failed",
            tool_name="search_code",
            error_content="File not found: /path/to/file",
        )

        assert error.tool_name == "search_code"
        assert error.error_content == "File not found: /path/to/file"
        assert error.details["tool_name"] == "search_code"
        assert error.details["error_content"] == "File not found: /path/to/file"

    def test_tool_error_without_error_content(self):
        """Test tool error without error content."""
        error = MCPToolError(
            "Tool not found",
            tool_name="invalid_tool",
        )

        assert error.tool_name == "invalid_tool"
        assert error.error_content is None


class TestExceptionHierarchy:
    """Tests for exception hierarchy."""

    def test_all_errors_are_mcp_error(self):
        """Test all exceptions inherit from MCPError."""
        errors = [
            MCPConnectionError("test"),
            MCPTimeoutError("test", timeout=30.0),
            MCPProtocolError("test"),
            MCPToolError("test", tool_name="test"),
        ]

        for error in errors:
            assert isinstance(error, MCPError)

    def test_can_catch_specific_errors(self):
        """Test specific errors can be caught separately."""
        with pytest.raises(MCPConnectionError):
            raise MCPConnectionError("Connection failed")

        with pytest.raises(MCPTimeoutError):
            raise MCPTimeoutError("Timeout", timeout=30.0)

    def test_can_catch_all_as_mcp_error(self):
        """Test all errors can be caught as MCPError."""
        with pytest.raises(MCPError):
            raise MCPConnectionError("Connection failed")

        with pytest.raises(MCPError):
            raise MCPToolError("Tool failed", tool_name="test")
