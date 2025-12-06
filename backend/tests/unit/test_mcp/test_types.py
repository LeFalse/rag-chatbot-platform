"""Tests for MCP types."""

import pytest

from app.mcp.types import MCPTool, MCPToolResult, MCPServerInfo


class TestMCPTool:
    """Tests for MCPTool dataclass."""

    def test_from_dict_with_complete_data(self):
        """Test creating MCPTool from complete dictionary."""
        data = {
            "name": "search_code",
            "description": "Search for code in repository",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "ref": {"type": "string", "default": "main"},
                },
                "required": ["query"],
            },
        }

        tool = MCPTool.from_dict(data)

        assert tool.name == "search_code"
        assert tool.description == "Search for code in repository"
        assert tool.input_schema["type"] == "object"
        assert "query" in tool.input_schema["properties"]
        assert tool.input_schema["required"] == ["query"]

    def test_from_dict_with_minimal_data(self):
        """Test creating MCPTool with minimal data uses defaults."""
        data = {}

        tool = MCPTool.from_dict(data)

        assert tool.name == ""
        assert tool.description == ""
        assert tool.input_schema["type"] == "object"
        assert tool.input_schema["properties"] == {}
        assert tool.input_schema["required"] == []

    def test_from_dict_handles_missing_input_schema(self):
        """Test that missing inputSchema is handled gracefully."""
        data = {
            "name": "list_files",
            "description": "List files in directory",
        }

        tool = MCPTool.from_dict(data)

        assert tool.name == "list_files"
        assert tool.input_schema == {
            "type": "object",
            "properties": {},
            "required": [],
        }


class TestMCPToolResult:
    """Tests for MCPToolResult dataclass."""

    def test_from_dict_with_text_content(self):
        """Test creating MCPToolResult from text content."""
        data = {
            "content": [
                {"type": "text", "text": "File content here"},
            ],
            "isError": False,
        }

        result = MCPToolResult.from_dict(data)

        assert result.text == "File content here"
        assert result.is_error is False

    def test_from_dict_with_multiple_text_items(self):
        """Test that multiple text items are concatenated."""
        data = {
            "content": [
                {"type": "text", "text": "Line 1"},
                {"type": "text", "text": "Line 2"},
                {"type": "text", "text": "Line 3"},
            ],
        }

        result = MCPToolResult.from_dict(data)

        assert result.text == "Line 1\nLine 2\nLine 3"

    def test_from_dict_filters_non_text_content(self):
        """Test that non-text content is filtered out."""
        data = {
            "content": [
                {"type": "text", "text": "Text content"},
                {"type": "image", "data": "base64..."},
                {"type": "text", "text": "More text"},
            ],
        }

        result = MCPToolResult.from_dict(data)

        assert result.text == "Text content\nMore text"

    def test_from_dict_with_error(self):
        """Test creating error result."""
        data = {
            "content": [
                {"type": "text", "text": "Error: File not found"},
            ],
            "isError": True,
        }

        result = MCPToolResult.from_dict(data)

        assert result.is_error is True
        assert "File not found" in result.text

    def test_from_dict_empty_content(self):
        """Test handling empty content list."""
        data = {"content": []}

        result = MCPToolResult.from_dict(data)

        assert result.text == ""
        assert result.is_error is False

    def test_text_property_with_missing_text_key(self):
        """Test text property handles items without text key."""
        result = MCPToolResult(
            content=[
                {"type": "text"},  # Missing text key
                {"type": "text", "text": "Valid text"},
            ]
        )

        assert result.text == "\nValid text"


class TestMCPServerInfo:
    """Tests for MCPServerInfo dataclass."""

    def test_default_protocol_version(self):
        """Test default protocol version is set."""
        info = MCPServerInfo(name="test-server", version="1.0.0")

        assert info.protocol_version == "2024-11-05"

    def test_custom_protocol_version(self):
        """Test custom protocol version can be set."""
        info = MCPServerInfo(
            name="test-server",
            version="1.0.0",
            protocol_version="2025-01-01",
        )

        assert info.protocol_version == "2025-01-01"
