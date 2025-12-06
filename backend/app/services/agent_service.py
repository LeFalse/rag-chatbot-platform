"""Agent service - implements RAG + tool calling agent loop."""

import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TypedDict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.exceptions import MCPToolError
from app.mcp.gitlab import GitLabConfig, GitLabMCP, create_gitlab_tools_for_llm
from app.models.message import Message
from app.providers.llm.base import BaseLLMProvider
from app.providers.llm.types import (
    AssistantMessageWithToolCalls,
    ChatMessage,
    LLMResponseWithTools,
    ToolCall,
    ToolDefinition,
    ToolMessage,
)
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.message_repo import MessageRepository
from app.services.cache.session_cache import SessionCache
from app.services.embedding_service import EmbeddingService
from app.services.language_utils import (
    LANGUAGE_INSTRUCTION,
    PERSONALITY_PROMPTS,
    detect_language_prefix,
    has_language_instruction,
)

logger = logging.getLogger(__name__)

# Type alias for all message types in agent conversation
AgentMessage = ChatMessage | ToolMessage | AssistantMessageWithToolCalls


class MCPConfig(TypedDict, total=False):
    """MCP configuration for agent."""

    gitlab: GitLabConfig | None


@dataclass
class AgentIteration:
    """Record of a single agent iteration."""

    iteration: int
    tool_calls: list[ToolCall]
    tool_results: list[dict[str, str]]
    tokens_input: int
    tokens_output: int


@dataclass
class AgentContext:
    """Context for agent execution."""

    question: str
    rag_context: str
    context_chunks: list[dict[str, str | float]]
    messages: list[AgentMessage]
    tools: list[ToolDefinition]


class AgentService:
    """Service for agent-based chat with RAG and tool calling.

    Implements an iterative agent loop that:
    1. Gets RAG context from collection documents
    2. Gets available tools from MCP (GitLab)
    3. Loops: LLM generates response -> execute tool calls -> repeat
    4. Returns final response when LLM provides content without tool calls
    """

    MAX_ITERATIONS = 10

    DEFAULT_SYSTEM_PROMPT = """You are an intelligent assistant with access to documentation AND code repository tools.

IMPORTANT: You MUST use the available tools to answer questions about code, files, or repositories.
DO NOT just explain what tools are available - actually CALL them!

Your capabilities:
1. **Documentation Context**: Relevant documentation excerpts are provided below
2. **Code Repository Tools**: You can search code, read files, and list repository contents

CRITICAL INSTRUCTIONS:
- When asked about code, files, or repository structure: USE THE TOOLS IMMEDIATELY
- Call get_file_contents to read files or list directories
- Call search_repositories to find code patterns
- DO NOT ask for more information if you can infer it from context
- The project_id is already configured - use it with the tools

ALWAYS prefer calling a tool over asking clarifying questions.
After gathering information via tools, provide a clear answer with specific file paths.

Do NOT:
- Just explain what tools exist without using them
- Ask for project_id - it's already configured
- Guess at file contents without actually reading them"""

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: BaseLLMProvider,
        embedding_service: EmbeddingService,
        session_cache: SessionCache | None = None,
    ):
        """Initialize agent service.

        Args:
            session: SQLAlchemy async session.
            llm_provider: LLM provider with tool calling support.
            embedding_service: Service for generating embeddings.
            session_cache: Optional cache for conversation context.
        """
        self.session = session
        self.llm_provider = llm_provider
        self.embedding_service = embedding_service
        self.session_cache = session_cache
        self.conv_repo = ConversationRepository(session)
        self.msg_repo = MessageRepository(session)
        self.chunk_repo = ChunkRepository(session)

    async def run_agent(
        self,
        conversation_id: UUID,
        collection_id: UUID,
        question: str,
        mcp_config: MCPConfig | None = None,
        *,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        collection_name: str = "",
        personality: str | None = None,
        system_prompt: str | None = None,
    ) -> AsyncIterator[str]:
        """Run agent to answer question with RAG and tools.

        Args:
            conversation_id: Conversation to add messages to.
            collection_id: Collection to search for RAG context.
            question: User's question.
            mcp_config: MCP configuration for tools.
            top_k: Number of RAG chunks to retrieve.
            similarity_threshold: Minimum similarity for RAG chunks.
            temperature: LLM temperature.
            max_tokens: Maximum tokens per LLM response.
            collection_name: Name of the collection (for display).
            personality: Agent personality setting.
            system_prompt: Custom system prompt override.

        Yields:
            Response content chunks (final response only).

        Raises:
            ValueError: If conversation not found.
            NotImplementedError: If LLM doesn't support tool calling.
        """
        start_time = time.time()

        # Verify conversation exists
        conversation = await self.conv_repo.get_with_messages(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Check LLM supports tool calling
        if not self.llm_provider.supports_tool_calling:
            raise NotImplementedError(
                f"LLM provider {self.llm_provider.provider_name} does not support tool calling. "
                "Use a compatible model like qwen3, llama3.1+, or mistral."
            )

        # Build agent context
        context = await self._build_context(
            question=question,
            collection_id=collection_id,
            conversation_id=conversation_id,
            mcp_config=mcp_config,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            system_prompt=system_prompt,
            personality=personality,
        )

        # Save user message
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=question,
        )
        self.session.add(user_message)
        await self.session.flush()

        if self.session_cache:
            await self.session_cache.add_message(str(conversation_id), "user", question)

        # Run agent loop
        iterations: list[AgentIteration] = []
        total_tokens_input = 0
        total_tokens_output = 0
        final_content = ""

        gitlab: GitLabMCP | None = None

        try:
            # Connect to MCP if configured
            if mcp_config and mcp_config.get("gitlab"):
                logger.info("Connecting to GitLab MCP...")
                gitlab = GitLabMCP(mcp_config["gitlab"])
                await gitlab.connect()
                # Update tools with actual available tools
                context.tools = create_gitlab_tools_for_llm(gitlab)
                logger.info("GitLab MCP connected, %d tools available", len(context.tools))

            # Agent loop
            for iteration in range(self.MAX_ITERATIONS):
                logger.debug(
                    "Agent iteration %d/%d for conversation %s (tools=%d)",
                    iteration + 1,
                    self.MAX_ITERATIONS,
                    conversation_id,
                    len(context.tools),
                )

                # Generate response with tools
                response = await self.llm_provider.generate_with_tools(
                    context.messages,
                    context.tools,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                total_tokens_input += response.tokens_input
                total_tokens_output += response.tokens_output

                logger.debug(
                    "LLM response: is_final=%s, has_tool_calls=%s, content_len=%d",
                    response.is_final_response,
                    response.has_tool_calls,
                    len(response.content or ""),
                )

                # Check if final response (content without tool calls)
                if response.is_final_response:
                    final_content = response.content or ""
                    logger.info(
                        "Agent completed after %d iterations",
                        iteration + 1,
                    )
                    break

                # Process tool calls
                if response.has_tool_calls and response.tool_calls:
                    iteration_record = AgentIteration(
                        iteration=iteration + 1,
                        tool_calls=response.tool_calls,
                        tool_results=[],
                        tokens_input=response.tokens_input,
                        tokens_output=response.tokens_output,
                    )

                    # Add assistant message with tool calls to history
                    self._add_assistant_tool_call_message(context.messages, response)

                    # Execute each tool call
                    for tool_call in response.tool_calls:
                        result = await self._execute_tool_call(
                            tool_call,
                            gitlab,
                        )
                        iteration_record.tool_results.append(result)

                        # Add tool result to messages
                        tool_message: ToolMessage = {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result["content"],
                        }
                        context.messages.append(tool_message)

                    iterations.append(iteration_record)

                # If we have content but also tool calls, continue iterating
                elif response.content:
                    # LLM provided content but might need more tools
                    final_content = response.content
                    break

            else:
                # Max iterations reached
                logger.warning(
                    "Agent reached max iterations (%d) for conversation %s",
                    self.MAX_ITERATIONS,
                    conversation_id,
                )
                if not final_content:
                    final_content = (
                        "I apologize, but I was unable to complete the analysis "
                        "within the allowed number of iterations. Please try a more specific question."
                    )

        finally:
            # Disconnect MCP
            if gitlab:
                await gitlab.disconnect()

        latency_ms = int((time.time() - start_time) * 1000)

        # Build full prompt string for debugging/display
        full_prompt = self._build_prompt_string(context.messages)

        # Build agent metadata
        agent_metadata = {
            "iterations": len(iterations),
            "total_tool_calls": sum(len(it.tool_calls) for it in iterations),
            "tools_used": list({
                tc.name
                for it in iterations
                for tc in it.tool_calls
            }),
        }

        # Save assistant message
        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=final_content,
            prompt_input=full_prompt,
            context_chunks=context.context_chunks,
            agent_config={
                # Collection config fields (for frontend display)
                "collection_name": collection_name,
                "personality": personality or "professional",
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_k": top_k,
                "system_prompt": system_prompt,
                # Agent-specific fields
                "type": "agent",
                "mcp_enabled": bool(mcp_config and mcp_config.get("gitlab")),
                "iterations": agent_metadata["iterations"],
                "tool_calls": agent_metadata["total_tool_calls"],
            },
            latency_ms=latency_ms,
            model=self.llm_provider.provider_name,
            tokens_input=total_tokens_input,
            tokens_output=total_tokens_output,
            tokens_used=total_tokens_input + total_tokens_output,
        )
        self.session.add(assistant_message)

        if self.session_cache:
            await self.session_cache.add_message(
                str(conversation_id),
                "assistant",
                final_content,
            )

        await self.session.commit()

        # Yield final response
        yield final_content

        # Yield sources metadata
        if context.context_chunks:
            sources_json = json.dumps({"sources": context.context_chunks})
            yield f"\n[SOURCES]{sources_json}[/SOURCES]"

    async def _build_context(
        self,
        question: str,
        collection_id: UUID,
        conversation_id: UUID,
        mcp_config: MCPConfig | None,
        top_k: int,
        similarity_threshold: float,
        system_prompt: str | None = None,
        personality: str | None = None,
    ) -> AgentContext:
        """Build context for agent execution.

        Args:
            question: User's question.
            collection_id: Collection for RAG context.
            conversation_id: Conversation for history.
            mcp_config: MCP configuration.
            top_k: Number of RAG chunks.
            similarity_threshold: Minimum similarity.
            system_prompt: Custom system prompt override.
            personality: Personality preset name.

        Returns:
            AgentContext with all necessary data.
        """
        # Get conversation history from cache
        messages: list[AgentMessage] = []
        if self.session_cache:
            cached = await self.session_cache.get_messages(
                str(conversation_id),
                limit=6,
            )
            messages = [
                ChatMessage(role=m["role"], content=m["content"])
                for m in cached
                if m["role"] in ("user", "assistant")
            ]

        # Get RAG context
        question_embedding = await self.embedding_service.embed_text(question)
        similar_chunks = await self.chunk_repo.search_similar(
            question_embedding,
            collection_id,
            limit=top_k,
            threshold=similarity_threshold,
        )

        rag_context = self._format_rag_context(similar_chunks)
        context_chunks = self._build_context_metadata(similar_chunks)

        # Build system message with project context
        project_context = ""
        if mcp_config and mcp_config.get("gitlab"):
            project_id = mcp_config["gitlab"].get("project_id", "")
            if project_id:
                project_context = f"""

## GitLab Repository Context
IMPORTANT: When calling any GitLab tool, use EXACTLY this project_id: "{project_id}"
DO NOT use placeholder values like "your_project_id" - use the actual value above."""

        # Build base prompt with personality
        prompt_parts = []
        if personality and personality in PERSONALITY_PROMPTS:
            prompt_parts.append(PERSONALITY_PROMPTS[personality])

        # Use custom system_prompt if provided, otherwise use default
        base_prompt = system_prompt if system_prompt else self.DEFAULT_SYSTEM_PROMPT
        prompt_parts.append(base_prompt)

        full_base_prompt = "\n\n".join(prompt_parts)

        # Only add default language instruction if custom prompt doesn't have one
        # This allows users to set specific language requirements in collection settings
        language_suffix = ""
        if not system_prompt or not has_language_instruction(system_prompt):
            language_suffix = LANGUAGE_INSTRUCTION

        system_content = (
            f"{full_base_prompt}{project_context}\n\n"
            f"## Documentation Context\n{rag_context}"
            f"{language_suffix}"
        )

        system_message = ChatMessage(role="system", content=system_content)

        # Build messages list
        if messages and messages[0].get("role") == "system":
            messages[0] = system_message
        else:
            messages.insert(0, system_message)

        # Detect language instruction and create prefix for user message
        lang_prefix = detect_language_prefix(system_prompt)
        question_for_llm = f"{lang_prefix}{question}" if lang_prefix else question

        # Add current question (with lang prefix for LLM only)
        messages.append(ChatMessage(role="user", content=question_for_llm))

        # Build placeholder tools (will be updated when MCP connects)
        tools: list[ToolDefinition] = []

        return AgentContext(
            question=question,
            rag_context=rag_context,
            context_chunks=context_chunks,
            messages=messages,
            tools=tools,
        )

    def _build_prompt_string(self, messages: list[AgentMessage]) -> str:
        """Build a readable prompt string from messages for debugging.

        Args:
            messages: List of chat messages.

        Returns:
            Formatted prompt string.
        """
        parts = []
        for msg in messages:
            role = msg.get("role", "unknown") if isinstance(msg, dict) else getattr(msg, "role", "unknown")
            content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
            parts.append(f"=== {role.upper()} ===\n{content}")
        return "\n\n".join(parts)

    def _format_rag_context(
        self,
        similar_chunks: list[tuple],
    ) -> str:
        """Format RAG chunks as context string.

        Args:
            similar_chunks: List of (chunk, score, filename) tuples.

        Returns:
            Formatted context string.
        """
        if not similar_chunks:
            return "No relevant documentation found."

        parts = []
        for chunk, score, filename in similar_chunks:
            parts.append(f"### {filename}\n{chunk.content}")

        return "\n\n".join(parts)

    def _build_context_metadata(
        self,
        similar_chunks: list[tuple],
    ) -> list[dict[str, str | float]]:
        """Build metadata for context chunks.

        Args:
            similar_chunks: List of (chunk, score, filename) tuples.

        Returns:
            List of metadata dicts.
        """
        if not similar_chunks:
            return []

        # Group by filename with highest score
        file_scores: dict[str, float] = {}
        for chunk, score, filename in similar_chunks:
            if filename not in file_scores or score > file_scores[filename]:
                file_scores[filename] = score

        return [
            {"filename": filename, "similarity_score": round(score, 4)}
            for filename, score in sorted(
                file_scores.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        ]

    def _add_assistant_tool_call_message(
        self,
        messages: list[AgentMessage],
        response: LLMResponseWithTools,
    ) -> None:
        """Add assistant message with tool calls to message history.

        Args:
            messages: Message list to append to.
            response: LLM response with tool calls.
        """
        if not response.tool_calls:
            return

        # Format tool calls for message history
        # NOTE: Ollama expects arguments as dict, not JSON string
        tool_calls_formatted: list[dict[str, str | dict[str, str]]] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": tc.arguments,
                },
            }
            for tc in response.tool_calls
        ]

        # Add as assistant message with tool calls
        assistant_msg: AssistantMessageWithToolCalls = {
            "role": "assistant",
            "content": response.content,
            "tool_calls": tool_calls_formatted,
        }
        messages.append(assistant_msg)

    async def _execute_tool_call(
        self,
        tool_call: ToolCall,
        gitlab: GitLabMCP | None,
    ) -> dict[str, str]:
        """Execute a single tool call.

        Args:
            tool_call: Tool call to execute.
            gitlab: GitLab MCP client (if connected).

        Returns:
            Dict with tool name and result content.
        """
        arguments = dict(tool_call.arguments)

        logger.info(
            "Executing tool: %s with args: %s",
            tool_call.name,
            arguments,
        )

        try:
            # Handle custom search_project_code tool (not MCP, calls GitLab API directly)
            if tool_call.name == "search_project_code":
                if gitlab and gitlab.is_connected:
                    query = str(arguments.get("query", ""))
                    content = await gitlab.search_project_code(query)
                else:
                    content = "Error: GitLab not connected"
                return {"tool_name": tool_call.name, "content": content}

            # Handle MCP tools
            # Auto-inject correct project_id for GitLab tools
            # LLMs often hallucinate project_ids, so we override with the configured one
            if gitlab and gitlab.is_connected and "project_id" in arguments:
                correct_project_id = gitlab.config["project_id"]
                if arguments["project_id"] != correct_project_id:
                    logger.info(
                        "Correcting project_id from '%s' to '%s'",
                        arguments["project_id"],
                        correct_project_id,
                    )
                    arguments["project_id"] = correct_project_id

            if gitlab and gitlab.is_connected:
                result = await gitlab.call_raw_tool(
                    tool_call.name,
                    arguments,
                )
                content = result.text
            else:
                content = f"Error: Tool {tool_call.name} is not available (MCP not connected)"

        except MCPToolError as e:
            logger.warning("Tool %s failed: %s", tool_call.name, e)
            content = f"Error executing {tool_call.name}: {e.message}"

        except Exception as e:
            logger.exception("Unexpected error executing tool %s", tool_call.name)
            content = f"Unexpected error executing {tool_call.name}: {e}"

        return {
            "tool_name": tool_call.name,
            "content": content,
        }
