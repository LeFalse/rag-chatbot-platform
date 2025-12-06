"""MCP client with JSON-RPC 2.0 over stdio transport."""

import asyncio
import json
import logging
import os
from collections.abc import Mapping

from app.mcp.exceptions import (
    MCPConnectionError,
    MCPProtocolError,
    MCPTimeoutError,
    MCPToolError,
)
from app.mcp.types import (
    JSONRPCNotification,
    JSONRPCRequest,
    JSONRPCResponse,
    MCPServerInfo,
    MCPTool,
    MCPToolResult,
)

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for communicating with MCP servers via JSON-RPC 2.0 over stdio.

    Implements the Model Context Protocol for tool discovery and execution.

    Usage:
        async with MCPClient() as client:
            await client.connect(["npx", "-y", "@anthropic-ai/mcp-server-gitlab"])
            tools = await client.list_tools()
            result = await client.call_tool("search_code", {"query": "logo"})
    """

    PROTOCOL_VERSION = "2024-11-05"
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        """Initialize MCP client.

        Args:
            timeout: Default timeout for operations in seconds.
        """
        self.timeout = timeout
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0
        self._server_info: MCPServerInfo | None = None
        self._read_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()

    async def __aenter__(self) -> "MCPClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if client is connected to an MCP server."""
        return self._process is not None and self._process.returncode is None

    @property
    def server_info(self) -> MCPServerInfo | None:
        """Get server information from initialization."""
        return self._server_info

    async def connect(
        self,
        command: list[str],
        env: Mapping[str, str] | None = None,
        *,
        cwd: str | None = None,
    ) -> MCPServerInfo:
        """Connect to an MCP server process.

        Args:
            command: Command to start the MCP server (e.g., ["npx", "-y", "server"]).
            env: Environment variables for the server process.
            cwd: Working directory for the server process.

        Returns:
            Server information from initialization.

        Raises:
            MCPConnectionError: If connection fails.
            MCPTimeoutError: If initialization times out.
        """
        if self.is_connected:
            raise MCPConnectionError(
                "Already connected to an MCP server",
                command=command,
            )

        try:
            # Merge environment with current env
            process_env = dict(os.environ)
            if env:
                process_env.update(env)

            self._process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
                cwd=cwd,
                limit=1024 * 1024,  # 1MB buffer for large tool responses
            )

            logger.info("Started MCP server process: %s (PID: %d)", command, self._process.pid)

        except FileNotFoundError as e:
            raise MCPConnectionError(
                f"Command not found: {command[0]}",
                command=command,
            ) from e
        except OSError as e:
            raise MCPConnectionError(
                f"Failed to start MCP server: {e}",
                command=command,
            ) from e

        # Initialize the MCP connection
        try:
            self._server_info = await self._initialize()
            return self._server_info
        except Exception:
            await self.disconnect()
            raise

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._process is None:
            return

        try:
            # Send graceful shutdown
            if self._process.stdin and not self._process.stdin.is_closing():
                self._process.stdin.close()
                await self._process.stdin.wait_closed()

            # Wait for process to exit
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("MCP server did not exit gracefully, terminating")
                self._process.terminate()
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=2.0)
                except asyncio.TimeoutError:
                    logger.warning("MCP server did not terminate, killing")
                    self._process.kill()
                    await self._process.wait()

            logger.info("MCP server disconnected")

        except ProcessLookupError:
            pass  # Process already exited
        finally:
            self._process = None
            self._server_info = None

    async def list_tools(self) -> list[MCPTool]:
        """List available tools from the MCP server.

        Returns:
            List of available tools.

        Raises:
            MCPConnectionError: If not connected.
            MCPProtocolError: If response is invalid.
        """
        self._ensure_connected()

        response = await self._send_request("tools/list", {})
        tools_data = response.get("tools", [])

        return [MCPTool.from_dict(tool) for tool in tools_data]

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, object],
    ) -> MCPToolResult:
        """Call a tool on the MCP server.

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool execution result.

        Raises:
            MCPConnectionError: If not connected.
            MCPToolError: If tool execution fails.
        """
        self._ensure_connected()

        try:
            response = await self._send_request(
                "tools/call",
                {"name": name, "arguments": arguments},
            )

            result = MCPToolResult.from_dict(response)

            if result.is_error:
                raise MCPToolError(
                    f"Tool '{name}' returned an error",
                    tool_name=name,
                    error_content=result.text,
                )

            return result

        except MCPProtocolError as e:
            # Check if this is a tool-specific error from JSON-RPC
            if e.response and "error" in e.response:
                error = e.response["error"]
                raise MCPToolError(
                    str(error.get("message", "Unknown tool error")),
                    tool_name=name,
                    error_content=str(error.get("data")),
                ) from e
            raise

    async def _initialize(self) -> MCPServerInfo:
        """Initialize the MCP connection with handshake.

        Returns:
            Server information.

        Raises:
            MCPProtocolError: If initialization fails.
            MCPTimeoutError: If initialization times out.
        """
        # Send initialize request
        response = await self._send_request(
            "initialize",
            {
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "rag-chatbot-mcp-client",
                    "version": "1.0.0",
                },
            },
        )

        # Parse server info
        server_info = response.get("serverInfo", {})
        protocol_version = response.get("protocolVersion", self.PROTOCOL_VERSION)

        info = MCPServerInfo(
            name=server_info.get("name", "unknown"),
            version=server_info.get("version", "unknown"),
            protocol_version=protocol_version,
        )

        # Send initialized notification
        await self._send_notification("notifications/initialized", {})

        logger.info(
            "MCP connection initialized: %s v%s (protocol %s)",
            info.name,
            info.version,
            info.protocol_version,
        )

        return info

    async def _send_request(
        self,
        method: str,
        params: dict[str, object],
    ) -> dict[str, object]:
        """Send a JSON-RPC request and wait for response.

        Args:
            method: RPC method name.
            params: Method parameters.

        Returns:
            Response result.

        Raises:
            MCPProtocolError: If response is invalid or contains error.
            MCPTimeoutError: If request times out.
        """
        self._request_id += 1
        request_id = self._request_id

        request: JSONRPCRequest = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        await self._write_message(request)

        try:
            response = await asyncio.wait_for(
                self._read_response(request_id),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError as e:
            raise MCPTimeoutError(
                f"Request '{method}' timed out after {self.timeout}s",
                timeout=self.timeout,
            ) from e

        # Check for error response
        if "error" in response:
            error = response["error"]
            raise MCPProtocolError(
                f"RPC error {error.get('code')}: {error.get('message')}",
                response=dict(response),
            )

        return response.get("result", {})

    async def _send_notification(
        self,
        method: str,
        params: dict[str, object],
    ) -> None:
        """Send a JSON-RPC notification (no response expected).

        Args:
            method: Notification method name.
            params: Method parameters.
        """
        notification: JSONRPCNotification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        await self._write_message(notification)

    async def _write_message(self, message: dict[str, object]) -> None:
        """Write a JSON-RPC message to the server.

        Args:
            message: Message to send.

        Raises:
            MCPConnectionError: If write fails.
        """
        if not self._process or not self._process.stdin:
            raise MCPConnectionError("Not connected to MCP server")

        async with self._write_lock:
            try:
                data = json.dumps(message) + "\n"
                self._process.stdin.write(data.encode())
                await self._process.stdin.drain()

                logger.debug("Sent: %s", message.get("method", "response"))

            except (BrokenPipeError, ConnectionResetError) as e:
                raise MCPConnectionError(
                    "Connection to MCP server lost",
                ) from e

    async def _read_response(self, request_id: int) -> JSONRPCResponse:
        """Read JSON-RPC response for a specific request ID.

        Args:
            request_id: Expected request ID.

        Returns:
            JSON-RPC response.

        Raises:
            MCPProtocolError: If response is invalid.
            MCPConnectionError: If read fails.
        """
        if not self._process or not self._process.stdout:
            raise MCPConnectionError("Not connected to MCP server")

        async with self._read_lock:
            while True:
                try:
                    line = await self._process.stdout.readline()
                    if not line:
                        # Check if process has exited
                        if self._process.returncode is not None:
                            stderr = ""
                            if self._process.stderr:
                                stderr_data = await self._process.stderr.read()
                                stderr = stderr_data.decode()
                            raise MCPConnectionError(
                                f"MCP server exited unexpectedly: {stderr}",
                            )
                        continue

                    try:
                        response = json.loads(line.decode())
                    except json.JSONDecodeError as e:
                        logger.warning("Invalid JSON from MCP server: %s", line)
                        raise MCPProtocolError(
                            f"Invalid JSON response: {e}",
                        ) from e

                    # Skip notifications (no id field)
                    if "id" not in response:
                        logger.debug("Received notification: %s", response.get("method"))
                        continue

                    # Check if this is our response
                    if response.get("id") == request_id:
                        logger.debug("Received response for request %d", request_id)
                        return response

                    # Wrong ID - log warning and continue
                    logger.warning(
                        "Received response for unexpected request ID: %s (expected %d)",
                        response.get("id"),
                        request_id,
                    )

                except (BrokenPipeError, ConnectionResetError) as e:
                    raise MCPConnectionError(
                        "Connection to MCP server lost",
                    ) from e

    def _ensure_connected(self) -> None:
        """Ensure client is connected.

        Raises:
            MCPConnectionError: If not connected.
        """
        if not self.is_connected:
            raise MCPConnectionError("Not connected to MCP server")
