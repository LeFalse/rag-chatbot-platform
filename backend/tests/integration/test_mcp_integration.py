"""Integration tests for MCP client.

Tests the MCP client against a real subprocess running a mock MCP server.
This verifies the JSON-RPC 2.0 communication over stdio actually works.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

import pytest

from app.mcp.client import MCPClient
from app.mcp.exceptions import MCPConnectionError, MCPProtocolError, MCPToolError
from app.mcp.types import MCPTool


# Mock MCP server script that implements the MCP protocol
MOCK_MCP_SERVER_SCRIPT = '''
"""Mock MCP server for testing."""
import json
import sys

def send_response(response):
    """Send a JSON-RPC response to stdout."""
    sys.stdout.write(json.dumps(response) + "\\n")
    sys.stdout.flush()

def main():
    """Main server loop."""
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
        except json.JSONDecodeError:
            continue

        method = request.get("method", "")
        request_id = request.get("id")
        params = request.get("params", {})

        # Handle initialize
        if method == "initialize":
            send_response({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "mock-mcp-server",
                        "version": "1.0.0",
                    },
                    "capabilities": {},
                },
            })

        # Handle notifications (no response needed)
        elif method == "notifications/initialized":
            pass  # No response for notifications

        # Handle tools/list
        elif method == "tools/list":
            send_response({
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        {
                            "name": "search_code",
                            "description": "Search for code in repository",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Search query",
                                    },
                                },
                                "required": ["query"],
                            },
                        },
                        {
                            "name": "read_file",
                            "description": "Read file contents",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "File path",
                                    },
                                },
                                "required": ["path"],
                            },
                        },
                    ],
                },
            })

        # Handle tools/call
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            if tool_name == "search_code":
                query = arguments.get("query", "")
                send_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"src/config.py:42:LOGO_PATH = \\"/assets/{query}.png\\"\\nsrc/utils.py:15:def get_{query}():",
                            },
                        ],
                        "isError": False,
                    },
                })

            elif tool_name == "read_file":
                path = arguments.get("path", "")
                send_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"# Contents of {path}\\nprint(\\"hello\\")",
                            },
                        ],
                        "isError": False,
                    },
                })

            elif tool_name == "error_tool":
                send_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": "Error: Something went wrong",
                            },
                        ],
                        "isError": True,
                    },
                })

            else:
                send_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}",
                    },
                })

        # Unknown method
        else:
            send_response({
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            })

if __name__ == "__main__":
    main()
'''


@pytest.fixture
def mock_server_script() -> str:
    """Create a temporary mock MCP server script."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
    ) as f:
        f.write(MOCK_MCP_SERVER_SCRIPT)
        return f.name


class TestMCPClientIntegration:
    """Integration tests for MCP client with real subprocess."""

    @pytest.mark.asyncio
    async def test_connect_and_initialize(self, mock_server_script: str):
        """Test connecting to MCP server and initializing."""
        async with MCPClient(timeout=10.0) as client:
            server_info = await client.connect([sys.executable, mock_server_script])

            assert client.is_connected
            assert server_info.name == "mock-mcp-server"
            assert server_info.version == "1.0.0"
            assert server_info.protocol_version == "2024-11-05"

    @pytest.mark.asyncio
    async def test_list_tools(self, mock_server_script: str):
        """Test listing available tools from server."""
        async with MCPClient(timeout=10.0) as client:
            await client.connect([sys.executable, mock_server_script])

            tools = await client.list_tools()

            assert len(tools) == 2

            tool_names = {t.name for t in tools}
            assert "search_code" in tool_names
            assert "read_file" in tool_names

            # Verify tool schema
            search_tool = next(t for t in tools if t.name == "search_code")
            assert search_tool.description == "Search for code in repository"
            assert "query" in search_tool.input_schema["properties"]

    @pytest.mark.asyncio
    async def test_call_tool_search(self, mock_server_script: str):
        """Test calling search_code tool."""
        async with MCPClient(timeout=10.0) as client:
            await client.connect([sys.executable, mock_server_script])

            result = await client.call_tool("search_code", {"query": "logo"})

            assert not result.is_error
            assert "src/config.py:42:" in result.text
            assert "logo" in result.text

    @pytest.mark.asyncio
    async def test_call_tool_read_file(self, mock_server_script: str):
        """Test calling read_file tool."""
        async with MCPClient(timeout=10.0) as client:
            await client.connect([sys.executable, mock_server_script])

            result = await client.call_tool("read_file", {"path": "src/main.py"})

            assert not result.is_error
            assert "src/main.py" in result.text
            assert "hello" in result.text

    @pytest.mark.asyncio
    async def test_call_unknown_tool_raises_error(self, mock_server_script: str):
        """Test calling unknown tool raises tool error."""
        async with MCPClient(timeout=10.0) as client:
            await client.connect([sys.executable, mock_server_script])

            with pytest.raises(MCPToolError) as exc_info:
                await client.call_tool("nonexistent", {})

            assert "Unknown tool" in str(exc_info.value)
            assert exc_info.value.tool_name == "nonexistent"

    @pytest.mark.asyncio
    async def test_multiple_sequential_calls(self, mock_server_script: str):
        """Test making multiple sequential tool calls."""
        async with MCPClient(timeout=10.0) as client:
            await client.connect([sys.executable, mock_server_script])

            # Make multiple calls
            result1 = await client.call_tool("search_code", {"query": "config"})
            result2 = await client.call_tool("read_file", {"path": "README.md"})
            result3 = await client.call_tool("search_code", {"query": "utils"})

            assert "config" in result1.text
            assert "README.md" in result2.text
            assert "utils" in result3.text

    @pytest.mark.asyncio
    async def test_disconnect_and_reconnect(self, mock_server_script: str):
        """Test disconnecting and reconnecting."""
        client = MCPClient(timeout=10.0)

        # First connection
        await client.connect([sys.executable, mock_server_script])
        assert client.is_connected

        tools1 = await client.list_tools()
        assert len(tools1) == 2

        # Disconnect
        await client.disconnect()
        assert not client.is_connected

        # Reconnect
        await client.connect([sys.executable, mock_server_script])
        assert client.is_connected

        tools2 = await client.list_tools()
        assert len(tools2) == 2

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_server_info_available_after_connect(self, mock_server_script: str):
        """Test server info is available after successful connection."""
        async with MCPClient(timeout=10.0) as client:
            await client.connect([sys.executable, mock_server_script])

            assert client.server_info is not None
            assert client.server_info.name == "mock-mcp-server"
