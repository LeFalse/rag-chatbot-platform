"""Tests for Agent Service."""

import json
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.providers.llm.types import (
    ChatMessage,
    LLMResponseWithTools,
    ToolCall,
    ToolDefinition,
    ToolMessage,
)
from app.services.agent_service import (
    AgentContext,
    AgentIteration,
    AgentService,
    MCPConfig,
)
from app.services.language_utils import has_language_instruction


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy session."""
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider with tool calling support."""
    provider = MagicMock()
    provider.provider_name = "ollama"
    provider.supports_tool_calling = True
    provider.generate_with_tools = AsyncMock()
    return provider


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    service = MagicMock()
    service.embed_text = AsyncMock(return_value=[0.1] * 768)
    return service


@pytest.fixture
def mock_session_cache():
    """Mock session cache."""
    cache = MagicMock()
    cache.get_messages = AsyncMock(return_value=[])
    cache.add_message = AsyncMock()
    return cache


@pytest.fixture
def agent_service(
    mock_session,
    mock_llm_provider,
    mock_embedding_service,
    mock_session_cache,
):
    """Create agent service with mocked dependencies."""
    return AgentService(
        session=mock_session,
        llm_provider=mock_llm_provider,
        embedding_service=mock_embedding_service,
        session_cache=mock_session_cache,
    )


class TestAgentServiceInit:
    """Tests for AgentService initialization."""

    def test_init_stores_dependencies(
        self,
        mock_session,
        mock_llm_provider,
        mock_embedding_service,
        mock_session_cache,
    ):
        """Test initialization stores all dependencies."""
        service = AgentService(
            session=mock_session,
            llm_provider=mock_llm_provider,
            embedding_service=mock_embedding_service,
            session_cache=mock_session_cache,
        )

        assert service.session == mock_session
        assert service.llm_provider == mock_llm_provider
        assert service.embedding_service == mock_embedding_service
        assert service.session_cache == mock_session_cache

    def test_max_iterations_constant(self, agent_service):
        """Test MAX_ITERATIONS is set."""
        assert agent_service.MAX_ITERATIONS == 10

    def test_default_system_prompt_exists(self, agent_service):
        """Test default system prompt is defined."""
        assert len(agent_service.DEFAULT_SYSTEM_PROMPT) > 100
        assert "documentation" in agent_service.DEFAULT_SYSTEM_PROMPT.lower()
        assert "tool" in agent_service.DEFAULT_SYSTEM_PROMPT.lower()


class TestFormatRagContext:
    """Tests for _format_rag_context method."""

    def test_empty_chunks_returns_no_documentation(self, agent_service):
        """Test empty chunks returns appropriate message."""
        result = agent_service._format_rag_context([])
        assert result == "No relevant documentation found."

    def test_single_chunk_formatted(self, agent_service):
        """Test single chunk is formatted correctly."""
        chunk = MagicMock()
        chunk.content = "This is the chunk content."
        chunks = [(chunk, 0.95, "README.md")]

        result = agent_service._format_rag_context(chunks)

        assert "### README.md" in result
        assert "This is the chunk content." in result

    def test_multiple_chunks_formatted(self, agent_service):
        """Test multiple chunks are formatted with separators."""
        chunk1 = MagicMock()
        chunk1.content = "Content from first file."
        chunk2 = MagicMock()
        chunk2.content = "Content from second file."

        chunks = [
            (chunk1, 0.95, "file1.md"),
            (chunk2, 0.85, "file2.md"),
        ]

        result = agent_service._format_rag_context(chunks)

        assert "### file1.md" in result
        assert "Content from first file." in result
        assert "### file2.md" in result
        assert "Content from second file." in result
        assert "\n\n" in result  # Separator between chunks


class TestBuildContextMetadata:
    """Tests for _build_context_metadata method."""

    def test_empty_chunks_returns_empty_list(self, agent_service):
        """Test empty chunks returns empty list."""
        result = agent_service._build_context_metadata([])
        assert result == []

    def test_single_chunk_metadata(self, agent_service):
        """Test single chunk metadata is built correctly."""
        chunk = MagicMock()
        chunks = [(chunk, 0.9512, "doc.md")]

        result = agent_service._build_context_metadata(chunks)

        assert len(result) == 1
        assert result[0]["filename"] == "doc.md"
        assert result[0]["similarity_score"] == 0.9512

    def test_multiple_chunks_same_file_takes_highest(self, agent_service):
        """Test multiple chunks from same file keeps highest score."""
        chunk1 = MagicMock()
        chunk2 = MagicMock()
        chunks = [
            (chunk1, 0.85, "file.md"),
            (chunk2, 0.95, "file.md"),
        ]

        result = agent_service._build_context_metadata(chunks)

        assert len(result) == 1
        assert result[0]["filename"] == "file.md"
        assert result[0]["similarity_score"] == 0.95

    def test_results_sorted_by_score_descending(self, agent_service):
        """Test results are sorted by score in descending order."""
        chunks = [
            (MagicMock(), 0.70, "low.md"),
            (MagicMock(), 0.95, "high.md"),
            (MagicMock(), 0.85, "mid.md"),
        ]

        result = agent_service._build_context_metadata(chunks)

        assert result[0]["filename"] == "high.md"
        assert result[1]["filename"] == "mid.md"
        assert result[2]["filename"] == "low.md"


class TestAddAssistantToolCallMessage:
    """Tests for _add_assistant_tool_call_message method."""

    def test_no_tool_calls_does_nothing(self, agent_service):
        """Test method does nothing when no tool calls."""
        messages: list[ChatMessage | ToolMessage] = []
        response = LLMResponseWithTools(
            content="Hello",
            tool_calls=None,
            model="test",
            tokens_input=10,
            tokens_output=5,
        )

        agent_service._add_assistant_tool_call_message(messages, response)

        assert len(messages) == 0

    def test_tool_calls_added_to_messages(self, agent_service):
        """Test tool calls are properly formatted and added."""
        messages: list[ChatMessage | ToolMessage] = []
        tool_call = ToolCall(
            id="call_1",
            name="search_code",
            arguments={"query": "logo"},
        )
        response = LLMResponseWithTools(
            content=None,
            tool_calls=[tool_call],
            model="test",
            tokens_input=10,
            tokens_output=5,
        )

        agent_service._add_assistant_tool_call_message(messages, response)

        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"
        assert "tool_calls" in messages[0]

    def test_multiple_tool_calls_formatted(self, agent_service):
        """Test multiple tool calls are all formatted."""
        messages: list[ChatMessage | ToolMessage] = []
        tool_calls = [
            ToolCall(id="call_1", name="search_code", arguments={"query": "logo"}),
            ToolCall(id="call_2", name="read_file", arguments={"path": "README.md"}),
        ]
        response = LLMResponseWithTools(
            content=None,
            tool_calls=tool_calls,
            model="test",
            tokens_input=10,
            tokens_output=5,
        )

        agent_service._add_assistant_tool_call_message(messages, response)

        assert len(messages) == 1
        assert len(messages[0]["tool_calls"]) == 2


class TestAgentTypes:
    """Tests for agent type classes."""

    def test_agent_iteration_creation(self):
        """Test AgentIteration dataclass."""
        tool_call = ToolCall(id="1", name="test", arguments={})
        iteration = AgentIteration(
            iteration=1,
            tool_calls=[tool_call],
            tool_results=[{"tool_name": "test", "content": "result"}],
            tokens_input=100,
            tokens_output=50,
        )

        assert iteration.iteration == 1
        assert len(iteration.tool_calls) == 1
        assert iteration.tokens_input == 100

    def test_agent_context_creation(self):
        """Test AgentContext dataclass."""
        context = AgentContext(
            question="Where is the logo?",
            rag_context="Documentation content here",
            context_chunks=[{"filename": "doc.md", "similarity_score": 0.9}],
            messages=[{"role": "user", "content": "test"}],
            tools=[],
        )

        assert context.question == "Where is the logo?"
        assert "Documentation" in context.rag_context

    def test_mcp_config_type(self):
        """Test MCPConfig TypedDict accepts gitlab config."""
        config: MCPConfig = {
            "gitlab": {
                "gitlab_url": "https://gitlab.com",
                "token": "test-token",
                "project_id": "group/project",
            }
        }

        assert config["gitlab"]["project_id"] == "group/project"


class TestAgentServiceValidation:
    """Tests for agent service validation."""

    @pytest.mark.asyncio
    async def test_run_agent_raises_for_unsupported_llm(
        self,
        mock_session,
        mock_embedding_service,
        mock_session_cache,
    ):
        """Test run_agent raises when LLM doesn't support tool calling."""
        mock_llm = MagicMock()
        mock_llm.supports_tool_calling = False
        mock_llm.provider_name = "test"

        service = AgentService(
            session=mock_session,
            llm_provider=mock_llm,
            embedding_service=mock_embedding_service,
            session_cache=mock_session_cache,
        )

        # Mock conversation repo
        with patch.object(service.conv_repo, "get_with_messages", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock()  # Conversation exists

            with pytest.raises(NotImplementedError) as exc_info:
                async for _ in service.run_agent(
                    conversation_id=uuid4(),
                    collection_id=uuid4(),
                    question="test",
                ):
                    pass

            assert "does not support tool calling" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_agent_raises_for_missing_conversation(
        self,
        agent_service,
    ):
        """Test run_agent raises when conversation not found."""
        with patch.object(
            agent_service.conv_repo,
            "get_with_messages",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = None

            with pytest.raises(ValueError) as exc_info:
                async for _ in agent_service.run_agent(
                    conversation_id=uuid4(),
                    collection_id=uuid4(),
                    question="test",
                ):
                    pass

            assert "not found" in str(exc_info.value)


class TestLanguageDetection:
    """Tests for language instruction detection (using language_utils module)."""

    def test_detects_english_language_instruction(self):
        """Test detection of English language keywords."""
        assert has_language_instruction("Always respond in English")
        assert has_language_instruction("Answer in Portuguese")
        assert has_language_instruction("LANGUAGE: Use English")

    def test_detects_portuguese_language_instruction(self):
        """Test detection of Portuguese language keywords."""
        assert has_language_instruction("Sempre responda em português")
        assert has_language_instruction("Responder em inglês")
        assert has_language_instruction("Idioma: Português")

    def test_detects_spanish_language_instruction(self):
        """Test detection of Spanish language keywords."""
        assert has_language_instruction("Siempre responde en español")
        assert has_language_instruction("Responder en inglés")

    def test_detects_italian_language_instruction(self):
        """Test detection of Italian language keywords."""
        assert has_language_instruction("Rispondi in italiano")
        assert has_language_instruction("Rispondere in inglese")

    def test_case_insensitive_detection(self):
        """Test detection is case insensitive."""
        assert has_language_instruction("RESPOND IN ENGLISH")
        assert has_language_instruction("Responda Em Português")
        assert has_language_instruction("IDIOMA: PT-BR")

    def test_no_detection_for_regular_text(self):
        """Test no false positives for regular text."""
        assert not has_language_instruction("You are a helpful assistant")
        assert not has_language_instruction("Answer questions about code")
        assert not has_language_instruction("Be professional and concise")
