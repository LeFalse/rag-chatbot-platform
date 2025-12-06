"""Tests for GitLab MCP wrapper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.mcp.exceptions import MCPConnectionError, MCPToolError
from app.mcp.gitlab import (
    FileContent,
    GitLabConfig,
    GitLabMCP,
    SearchResult,
    create_gitlab_tools_for_llm,
)
from app.mcp.types import MCPTool, MCPToolResult


@pytest.fixture
def gitlab_config() -> GitLabConfig:
    """Sample GitLab configuration."""
    return GitLabConfig(
        gitlab_url="https://gitlab.example.com",
        token="glpat-test-token",
        project_id="group/project",
    )


class TestGitLabConfig:
    """Tests for GitLabConfig type."""

    def test_gitlab_config_fields(self, gitlab_config: GitLabConfig):
        """Test GitLabConfig has required fields."""
        assert gitlab_config["gitlab_url"] == "https://gitlab.example.com"
        assert gitlab_config["token"] == "glpat-test-token"
        assert gitlab_config["project_id"] == "group/project"


class TestFileContent:
    """Tests for FileContent dataclass."""

    def test_file_content_creation(self):
        """Test FileContent creation."""
        content = FileContent(
            path="src/main.py",
            content="print('hello')",
            ref="main",
        )

        assert content.path == "src/main.py"
        assert content.content == "print('hello')"
        assert content.ref == "main"

    def test_file_content_default_ref(self):
        """Test FileContent default ref is main."""
        content = FileContent(path="file.txt", content="data")
        assert content.ref == "main"


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_search_result_creation(self):
        """Test SearchResult creation."""
        result = SearchResult(
            file_path="src/config.py",
            matched_line="LOGO_PATH = '/assets/logo.png'",
            line_number=42,
        )

        assert result.file_path == "src/config.py"
        assert result.matched_line == "LOGO_PATH = '/assets/logo.png'"
        assert result.line_number == 42


class TestGitLabMCPInit:
    """Tests for GitLabMCP initialization."""

    def test_init_stores_config(self, gitlab_config: GitLabConfig):
        """Test initialization stores configuration."""
        gitlab = GitLabMCP(gitlab_config)

        assert gitlab.config == gitlab_config
        assert gitlab.is_connected is False

    def test_init_custom_timeout(self, gitlab_config: GitLabConfig):
        """Test custom timeout can be set."""
        gitlab = GitLabMCP(gitlab_config, timeout=120.0)
        assert gitlab._client.timeout == 120.0

    def test_available_tools_empty_when_not_connected(self, gitlab_config: GitLabConfig):
        """Test available_tools is empty when not connected."""
        gitlab = GitLabMCP(gitlab_config)
        assert gitlab.available_tools == []


class TestGitLabMCPOperations:
    """Tests for GitLabMCP operations."""

    @pytest.mark.asyncio
    async def test_search_code_when_not_connected_raises(
        self, gitlab_config: GitLabConfig
    ):
        """Test search_code raises when not connected."""
        gitlab = GitLabMCP(gitlab_config)

        with pytest.raises(MCPConnectionError):
            await gitlab.search_code("logo")

    @pytest.mark.asyncio
    async def test_read_file_when_not_connected_raises(
        self, gitlab_config: GitLabConfig
    ):
        """Test read_file raises when not connected."""
        gitlab = GitLabMCP(gitlab_config)

        with pytest.raises(MCPConnectionError):
            await gitlab.read_file("README.md")

    @pytest.mark.asyncio
    async def test_list_directory_when_not_connected_raises(
        self, gitlab_config: GitLabConfig
    ):
        """Test list_directory raises when not connected."""
        gitlab = GitLabMCP(gitlab_config)

        with pytest.raises(MCPConnectionError):
            await gitlab.list_directory()

    @pytest.mark.asyncio
    async def test_call_tool_not_available_raises(
        self, gitlab_config: GitLabConfig
    ):
        """Test calling unavailable tool raises error."""
        gitlab = GitLabMCP(gitlab_config)
        gitlab._client._process = MagicMock(returncode=None)  # Mock as connected
        gitlab._tools = {}  # No tools available

        with pytest.raises(MCPToolError) as exc_info:
            await gitlab._call_tool("nonexistent_tool", {})

        assert "not available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_context_manager_connects_and_disconnects(
        self, gitlab_config: GitLabConfig
    ):
        """Test context manager handles connection lifecycle."""
        gitlab = GitLabMCP(gitlab_config)

        with patch.object(gitlab, "connect", new_callable=AsyncMock) as mock_connect:
            with patch.object(gitlab, "disconnect", new_callable=AsyncMock) as mock_disconnect:
                async with gitlab:
                    mock_connect.assert_called_once()

                mock_disconnect.assert_called_once()


class TestGitLabMCPSearchParsing:
    """Tests for search result parsing."""

    def test_parse_search_results_standard_format(self):
        """Test parsing search results in file:line:content format."""
        # Simulate parsing logic from search_code
        raw_output = """src/config.py:42:LOGO_PATH = '/assets/logo.png'
src/utils.py:15:def get_logo():"""

        results: list[SearchResult] = []
        for line in raw_output.split("\n"):
            if not line.strip():
                continue
            parts = line.split(":", 2)
            if len(parts) >= 3:
                results.append(
                    SearchResult(
                        file_path=parts[0],
                        line_number=int(parts[1]) if parts[1].isdigit() else 0,
                        matched_line=parts[2],
                    )
                )

        assert len(results) == 2
        assert results[0].file_path == "src/config.py"
        assert results[0].line_number == 42
        assert "LOGO_PATH" in results[0].matched_line

    def test_parse_search_results_file_only_format(self):
        """Test parsing search results with file path only."""
        raw_output = "src/logo.png"

        results: list[SearchResult] = []
        for line in raw_output.split("\n"):
            if not line.strip():
                continue
            parts = line.split(":", 2)
            if len(parts) >= 1:
                results.append(
                    SearchResult(
                        file_path=parts[0],
                        line_number=0,
                        matched_line=line,
                    )
                )

        assert len(results) == 1
        assert results[0].file_path == "src/logo.png"


class TestCreateGitLabToolsForLLM:
    """Tests for tool definition conversion."""

    def test_create_tools_from_mcp_tools(self, gitlab_config: GitLabConfig):
        """Test converting MCP tools to LLM format."""
        gitlab = GitLabMCP(gitlab_config)
        # Use tools from ESSENTIAL_GITLAB_TOOLS so they pass the filter
        gitlab._tools = {
            "get_file_contents": MCPTool(
                name="get_file_contents",
                description="Get file contents",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                    },
                    "required": ["path"],
                },
            ),
            "get_repository_tree": MCPTool(
                name="get_repository_tree",
                description="Get repository tree",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path"},
                    },
                    "required": [],
                },
            ),
        }

        tools = create_gitlab_tools_for_llm(gitlab)

        # 1 custom tool (search_project_code) + 2 MCP tools from ESSENTIAL_GITLAB_TOOLS
        assert len(tools) == 3

        # Check tool format
        tool_names = {t["function"]["name"] for t in tools}
        assert "search_project_code" in tool_names  # Custom tool always included first
        assert "get_file_contents" in tool_names
        assert "get_repository_tree" in tool_names

        # Check structure
        for tool in tools:
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]

    def test_create_tools_includes_custom_search_when_no_mcp_tools(self, gitlab_config: GitLabConfig):
        """Test always includes custom search_project_code tool even without MCP tools."""
        gitlab = GitLabMCP(gitlab_config)
        gitlab._tools = {}

        tools = create_gitlab_tools_for_llm(gitlab)

        # Custom search_project_code tool is always included
        assert len(tools) == 1
        assert tools[0]["function"]["name"] == "search_project_code"
