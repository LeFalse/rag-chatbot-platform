"""GitLab MCP server wrapper.

Provides a high-level interface for interacting with GitLab repositories
via the MCP protocol.
"""

import logging
from dataclasses import dataclass
from typing import TypedDict

import httpx

from app.mcp.client import MCPClient
from app.mcp.exceptions import MCPConnectionError, MCPToolError
from app.mcp.types import MCPTool, MCPToolResult

logger = logging.getLogger(__name__)


class GitLabConfig(TypedDict):
    """Configuration for GitLab MCP connection."""

    gitlab_url: str
    token: str
    project_id: str


@dataclass
class FileContent:
    """Content of a file from GitLab."""

    path: str
    content: str
    ref: str = "main"


@dataclass
class SearchResult:
    """Result from code search."""

    file_path: str
    matched_line: str
    line_number: int


class GitLabMCP:
    """High-level wrapper for GitLab MCP server.

    Provides convenient methods for common GitLab operations:
    - Search code in repository
    - Read file contents
    - List directory contents
    - Get repository structure

    Usage:
        config = GitLabConfig(
            gitlab_url="https://gitlab.com",
            token="glpat-xxx",
            project_id="group/project",
        )
        async with GitLabMCP(config) as gitlab:
            results = await gitlab.search_code("logo")
            content = await gitlab.read_file("src/config.ts")
    """

    # MCP server command - uses the better GitLab MCP server with more tools
    MCP_SERVER_COMMAND = ["npx", "-y", "@zereight/mcp-gitlab"]

    def __init__(self, config: GitLabConfig, timeout: float = 60.0):
        """Initialize GitLab MCP wrapper.

        Args:
            config: GitLab configuration.
            timeout: Timeout for MCP operations in seconds.
        """
        self.config = config
        self._client = MCPClient(timeout=timeout)
        self._tools: dict[str, MCPTool] = {}

    async def __aenter__(self) -> "GitLabMCP":
        """Connect to GitLab MCP server."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Disconnect from GitLab MCP server."""
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if connected to MCP server."""
        return self._client.is_connected

    @property
    def available_tools(self) -> list[str]:
        """Get list of available tool names."""
        return list(self._tools.keys())

    async def connect(self) -> None:
        """Connect to the GitLab MCP server.

        Raises:
            MCPConnectionError: If connection fails.
        """
        env = {
            "GITLAB_PERSONAL_ACCESS_TOKEN": self.config["token"],
            "GITLAB_URL": self.config["gitlab_url"],
        }

        logger.info(
            "Connecting to GitLab MCP for project: %s",
            self.config["project_id"],
        )

        await self._client.connect(self.MCP_SERVER_COMMAND, env=env)

        # Cache available tools
        tools = await self._client.list_tools()
        self._tools = {tool.name: tool for tool in tools}

        logger.info(
            "GitLab MCP connected. Available tools: %s",
            list(self._tools.keys()),
        )

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        await self._client.disconnect()
        self._tools.clear()

    async def search_code(
        self,
        query: str,
        *,
        ref: str = "main",
    ) -> list[SearchResult]:
        """Search for code in the repository.

        Args:
            query: Search query string.
            ref: Git reference (branch/tag/commit). Defaults to main.

        Returns:
            List of search results with file paths and matched lines.

        Raises:
            MCPToolError: If search fails.
        """
        result = await self._call_tool(
            "search_repositories",
            {
                "search_query": query,
                "project_id": self.config["project_id"],
            },
        )

        # Parse search results
        search_results: list[SearchResult] = []
        for line in result.text.split("\n"):
            if not line.strip():
                continue
            # Parse result format: file_path:line_number:matched_line
            parts = line.split(":", 2)
            if len(parts) >= 3:
                search_results.append(
                    SearchResult(
                        file_path=parts[0],
                        line_number=int(parts[1]) if parts[1].isdigit() else 0,
                        matched_line=parts[2],
                    )
                )
            elif len(parts) >= 1:
                search_results.append(
                    SearchResult(
                        file_path=parts[0],
                        line_number=0,
                        matched_line=line,
                    )
                )

        return search_results

    async def read_file(
        self,
        path: str,
        *,
        ref: str = "main",
    ) -> FileContent:
        """Read file contents from the repository.

        Args:
            path: File path relative to repository root.
            ref: Git reference (branch/tag/commit). Defaults to main.

        Returns:
            File content with path and reference.

        Raises:
            MCPToolError: If file read fails.
        """
        result = await self._call_tool(
            "get_file_contents",
            {
                "project_id": self.config["project_id"],
                "file_path": path,
                "ref": ref,
            },
        )

        return FileContent(
            path=path,
            content=result.text,
            ref=ref,
        )

    async def list_directory(
        self,
        path: str = "",
        *,
        ref: str = "main",
        recursive: bool = False,
    ) -> list[str]:
        """List contents of a directory in the repository.

        Args:
            path: Directory path relative to repository root. Empty for root.
            ref: Git reference (branch/tag/commit). Defaults to main.
            recursive: Whether to list recursively.

        Returns:
            List of file/directory paths.

        Raises:
            MCPToolError: If listing fails.
        """
        result = await self._call_tool(
            "get_repository_tree",
            {
                "project_id": self.config["project_id"],
                "path": path,
                "ref": ref,
                "recursive": recursive,
            },
        )

        # Parse tree output - each line is a path
        paths = [line.strip() for line in result.text.split("\n") if line.strip()]
        return paths

    async def get_repository_structure(
        self,
        *,
        ref: str = "main",
        max_depth: int = 3,
    ) -> str:
        """Get repository structure as a tree view.

        Args:
            ref: Git reference (branch/tag/commit). Defaults to main.
            max_depth: Maximum depth to traverse.

        Returns:
            Tree-like string representation of repository structure.

        Raises:
            MCPToolError: If operation fails.
        """
        result = await self._call_tool(
            "get_repository_tree",
            {
                "project_id": self.config["project_id"],
                "ref": ref,
                "recursive": True,
            },
        )

        return result.text

    async def search_project_code(
        self,
        query: str,
        *,
        ref: str = "main",
    ) -> str:
        """Search code within project using GitLab API directly.

        This is a custom tool that bypasses MCP to use GitLab's project search
        API, which searches WITHIN the project (not globally like MCP's
        search_repositories).

        Args:
            query: Search term (e.g., 'logo', 'login', 'config').
            ref: Git branch (default: main).

        Returns:
            Formatted search results with file paths and matched content.

        Raises:
            httpx.HTTPStatusError: If GitLab API call fails.
        """
        project_id = self.config["project_id"]
        gitlab_url = self.config["gitlab_url"].rstrip("/")
        token = self.config["token"]

        # URL encode project_id for path-based IDs (e.g., "group/project")
        encoded_project = project_id.replace("/", "%2F")

        url = f"{gitlab_url}/api/v4/projects/{encoded_project}/search"
        params = {
            "scope": "blobs",
            "search": query,
            "ref": ref,
            "per_page": 20,
        }
        headers = {"PRIVATE-TOKEN": token}

        logger.info(
            "Searching project %s for '%s' (ref: %s)",
            project_id,
            query,
            ref,
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            results = response.json()

        if not results:
            return f"No results found for '{query}' in project {project_id}"

        # Format results for LLM
        output_lines = [f"Found {len(results)} results for '{query}':\n"]
        for item in results:
            path = item.get("path", "unknown")
            startline = item.get("startline", 0)
            data = item.get("data", "").strip()[:200]  # Truncate long matches

            output_lines.append(f"**{path}**")
            if startline and data:
                output_lines.append(f"   Line {startline}: {data}")
            output_lines.append("")

        logger.info("Search returned %d results", len(results))

        return "\n".join(output_lines)

    async def get_tool(self, name: str) -> MCPTool | None:
        """Get a specific tool definition by name.

        Args:
            name: Tool name.

        Returns:
            Tool definition or None if not found.
        """
        return self._tools.get(name)

    async def call_raw_tool(
        self,
        name: str,
        arguments: dict[str, object],
    ) -> MCPToolResult:
        """Call any available MCP tool directly.

        This allows access to all GitLab MCP tools, not just the
        high-level methods provided by this wrapper.

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Raw tool result.

        Raises:
            MCPToolError: If tool call fails.
        """
        return await self._call_tool(name, arguments)

    async def _call_tool(
        self,
        name: str,
        arguments: dict[str, object],
    ) -> MCPToolResult:
        """Call an MCP tool.

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool result.

        Raises:
            MCPConnectionError: If not connected.
            MCPToolError: If tool call fails.
        """
        if not self.is_connected:
            raise MCPConnectionError("Not connected to GitLab MCP server")

        if name not in self._tools:
            available = ", ".join(self._tools.keys()) or "none"
            raise MCPToolError(
                f"Tool '{name}' not available. Available tools: {available}",
                tool_name=name,
            )

        logger.debug("Calling GitLab tool: %s with args: %s", name, arguments)

        result = await self._client.call_tool(name, arguments)

        logger.debug("Tool %s returned %d bytes", name, len(result.text))

        return result


# Tools most useful for code exploration and search
# Limiting tools improves LLM accuracy (77 tools overwhelms the model)
# NOTE: search_repositories is REMOVED - it searches globally, not within project
ESSENTIAL_GITLAB_TOOLS = frozenset({
    # Code exploration (search_repositories replaced by custom search_project_code)
    "get_file_contents",    # Read file contents
    "get_repository_tree",  # List directory contents
    # Commit history (useful for understanding changes)
    "list_commits",         # List commits with filtering
    "get_commit",           # Get commit details
    "get_commit_diff",      # Get commit changes
    # Project info
    "get_project",          # Get project details
})

# Custom tool for project-scoped code search (bypasses MCP, uses GitLab API directly)
CUSTOM_SEARCH_TOOL: dict[str, object] = {
    "type": "function",
    "function": {
        "name": "search_project_code",
        "description": (
            "Search for code, files, or text patterns within the project repository. "
            "Returns file paths and matching line content. Use this to find where "
            "specific code, configuration, images, or files are located in the project."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term (e.g., 'logo', 'login', 'config', 'database')",
                },
            },
            "required": ["query"],
        },
    },
}


def create_gitlab_tools_for_llm(gitlab: GitLabMCP) -> list[dict[str, object]]:
    """Create tool definitions in OpenAI/Ollama format for LLM.

    Converts MCP tools to the format expected by LLM providers.
    Includes custom search_project_code tool FIRST (most important for discovery),
    then filters MCP tools to only essential ones for code exploration.

    Args:
        gitlab: Connected GitLab MCP instance.

    Returns:
        List of tool definitions for LLM.
    """
    tools: list[dict[str, object]] = []

    # Add custom search tool FIRST - most useful for code discovery
    # This tool uses GitLab API directly to search WITHIN the project
    tools.append(CUSTOM_SEARCH_TOOL)

    # Add filtered MCP tools
    for tool in gitlab._tools.values():
        # Only include essential tools for code exploration
        if tool.name not in ESSENTIAL_GITLAB_TOOLS:
            continue

        tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema,
            },
        })

    return tools
