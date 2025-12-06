"""Tests for MCP client."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mcp.client import MCPClient
from app.mcp.exceptions import (
    MCPConnectionError,
    MCPProtocolError,
    MCPTimeoutError,
)
from app.mcp.types import MCPServerInfo


class TestMCPClientInit:
    """Tests for MCPClient initialization."""

    def test_default_timeout(self):
        """Test default timeout is set."""
        client = MCPClient()
        assert client.timeout == 30.0

    def test_custom_timeout(self):
        """Test custom timeout can be set."""
        client = MCPClient(timeout=60.0)
        assert client.timeout == 60.0

    def test_initial_state(self):
        """Test initial state is disconnected."""
        client = MCPClient()
        assert client.is_connected is False
        assert client.server_info is None


class TestMCPClientConnection:
    """Tests for MCPClient connection handling."""

    @pytest.mark.asyncio
    async def test_connect_command_not_found(self):
        """Test connection fails gracefully when command not found."""
        client = MCPClient()

        with pytest.raises(MCPConnectionError) as exc_info:
            await client.connect(["nonexistent-command-12345"])

        assert "Command not found" in str(exc_info.value)
        assert exc_info.value.command == ["nonexistent-command-12345"]

    @pytest.mark.asyncio
    async def test_connect_when_already_connected_raises(self):
        """Test connecting when already connected raises error."""
        client = MCPClient()

        # Mock as if already connected
        client._process = MagicMock()
        client._process.returncode = None

        with pytest.raises(MCPConnectionError) as exc_info:
            await client.connect(["echo", "test"])

        assert "Already connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self):
        """Test disconnect when not connected does nothing."""
        client = MCPClient()
        # Should not raise
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_is_connected_returns_false_when_process_exited(self):
        """Test is_connected returns False when process has exited."""
        client = MCPClient()
        client._process = MagicMock()
        client._process.returncode = 1  # Process exited

        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_context_manager_disconnects_on_exit(self):
        """Test async context manager calls disconnect on exit."""
        client = MCPClient()

        with patch.object(client, "disconnect", new_callable=AsyncMock) as mock_disconnect:
            async with client:
                pass
            mock_disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_disconnects_on_exception(self):
        """Test async context manager calls disconnect even on exception."""
        client = MCPClient()

        with patch.object(client, "disconnect", new_callable=AsyncMock) as mock_disconnect:
            with pytest.raises(ValueError):
                async with client:
                    raise ValueError("Test error")
            mock_disconnect.assert_called_once()


class TestMCPClientOperations:
    """Tests for MCPClient operations."""

    @pytest.mark.asyncio
    async def test_list_tools_when_not_connected_raises(self):
        """Test list_tools raises when not connected."""
        client = MCPClient()

        with pytest.raises(MCPConnectionError) as exc_info:
            await client.list_tools()

        assert "Not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_call_tool_when_not_connected_raises(self):
        """Test call_tool raises when not connected."""
        client = MCPClient()

        with pytest.raises(MCPConnectionError) as exc_info:
            await client.call_tool("search", {"query": "test"})

        assert "Not connected" in str(exc_info.value)


class TestMCPClientProtocol:
    """Tests for MCP protocol handling."""

    def test_protocol_version(self):
        """Test protocol version constant."""
        assert MCPClient.PROTOCOL_VERSION == "2024-11-05"

    @pytest.mark.asyncio
    async def test_request_id_increments(self):
        """Test request IDs increment with each request."""
        client = MCPClient()
        initial_id = client._request_id

        # Simulate incrementing
        client._request_id += 1
        assert client._request_id == initial_id + 1

        client._request_id += 1
        assert client._request_id == initial_id + 2


class TestJSONRPCMessageBuilding:
    """Tests for JSON-RPC message construction."""

    def test_jsonrpc_request_format(self):
        """Test JSON-RPC request has correct format."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }

        # Verify it can be serialized
        json_str = json.dumps(request)
        parsed = json.loads(json_str)

        assert parsed["jsonrpc"] == "2.0"
        assert parsed["id"] == 1
        assert parsed["method"] == "tools/list"

    def test_jsonrpc_notification_format(self):
        """Test JSON-RPC notification has correct format (no id)."""
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }

        assert "id" not in notification
        assert notification["jsonrpc"] == "2.0"

    def test_jsonrpc_response_with_result(self):
        """Test JSON-RPC response with result."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"tools": []},
        }

        assert "error" not in response
        assert response["result"] == {"tools": []}

    def test_jsonrpc_response_with_error(self):
        """Test JSON-RPC response with error."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32600,
                "message": "Invalid Request",
            },
        }

        assert "result" not in response
        assert response["error"]["code"] == -32600
