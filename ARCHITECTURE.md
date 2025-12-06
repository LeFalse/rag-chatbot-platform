# Architecture Overview

This document describes the architectural decisions and design patterns used in this project.

## Design Principles

### SOLID Principles

| Principle | Application |
|-----------|-------------|
| **Single Responsibility** | Each service handles one domain (Chat, Document, Embedding) |
| **Open/Closed** | Providers are extensible via new implementations |
| **Liskov Substitution** | Any LLM provider can replace another |
| **Interface Segregation** | Separate interfaces for LLM and Embedding |
| **Dependency Inversion** | Services depend on abstractions, not implementations |

### Design Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| Repository | `repositories/` | Abstract data access |
| Factory | `providers/*/factory.py` | Create providers based on config |
| Strategy | `providers/` | Interchangeable LLM/Embedding strategies |
| Dependency Injection | `api/deps.py` | Decouple dependencies |
| DTO | `schemas/` | Data transfer between layers |
| Adapter | `mcp/` | Adapt MCP protocol to internal tool types |

## Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                            │
│  - HTTP routes                                              │
│  - Request validation (Pydantic)                            │
│  - Response serialization                                   │
│  - Middleware (auth, logging, rate limiting)                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                          │
│  - Business logic orchestration                             │
│  - ChatService: RAG pipeline                                │
│  - AgentService: Tool calling loop with MCP                 │
│  - DocumentService: upload, chunking                        │
│  - EmbeddingService: vector generation                      │
│  - MetricsService: usage tracking                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Provider Layer                          │
│  - External service abstractions                            │
│  - LLM: OpenAI, Ollama                                     │
│  - Embedding: OpenAI, Ollama                               │
│  - Easily extensible for new providers                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Repository Layer                         │
│  - Data access abstraction                                  │
│  - DocumentRepository                                       │
│  - VectorRepository (pgvector)                              │
│  - ConversationRepository                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Data Layer                            │
│  - PostgreSQL + pgvector                                    │
│  - Redis (cache)                                            │
└─────────────────────────────────────────────────────────────┘
```

## Caching Strategy

### 1. Embedding Cache
- **Key**: `emb:{md5(text)}`
- **TTL**: 24 hours
- **Rationale**: Embeddings are deterministic; same input = same output

### 2. Session Cache
- **Key**: `conv:{conversation_id}:messages`
- **TTL**: 30 minutes (sliding)
- **Rationale**: Keep recent conversation context in memory

### 3. Rate Limiting
- **Key**: `rate:{api_key}:{endpoint}`
- **Algorithm**: Sliding window counter
- **Limits**: 60 req/min (chat), 100 req/min (other)

## Database Schema

```sql
-- Vector search with HNSW index: O(log n)
CREATE INDEX chunks_embedding_idx ON chunks
USING hnsw (embedding vector_cosine_ops);
```

### Tables
- `collections` - Groups of documents
- `documents` - Uploaded files metadata
- `chunks` - Document pieces with embeddings
- `conversations` - Chat sessions
- `messages` - Chat messages
- `metrics` - Usage tracking

## RAG Pipeline

```
1. Document Ingestion PDF/TXT → Extract text → Chunk (512 tokens, 50 overlap) → Generate embeddings → Store in pgvector

2. Query Processing
   User question → Generate embedding → Vector similarity search → Retrieve top-k chunks → Build context prompt → LLM generates response → Stream via SSE
```

## MCP Integration (Tool Calling)

The platform supports tool calling via the Model Context Protocol (MCP) for LLMs that support function calling. Currently, only GitLab is available as an MCP server.

### Chat Flow Decision

```
User sends question
        │
        ▼
┌───────────────────┐
│ Collection has    │
│ MCP configured?   │
└───────────────────┘
        │
   ┌────┴────┐
   │         │
  Yes        No
   │         │
   ▼         ▼
┌──────┐  ┌──────────┐
│Agent │  │ Simple   │
│Service│  │ RAG Chat │
└──────┘  └──────────┘
```

- **Simple RAG (ChatService)**: Document retrieval + LLM response, no tool calling
- **Agent Mode (AgentService)**: RAG context + tool calling loop with MCP

### Agent Loop

```
1. User question + RAG context → LLM with tools
2. If LLM returns tool_calls:
   - Execute each tool via MCP client
   - Append tool results to messages
   - Return to step 1 (max 10 iterations)
3. If LLM returns text: Stream response to user
```

### Available Tools (GitLab)

| Tool | Description |
|------|-------------|
| `search_repository` | Search for files by name pattern |
| `get_file_contents` | Read file content from repository |
| `list_issues` | List project issues with filters |
| `get_issue` | Get issue details |
| `list_merge_requests` | List merge requests with filters |
| `get_merge_request` | Get MR details and changes |

### Configuration

MCP is configured per-collection via the frontend settings. Requires:
- `GITLAB_TOKEN` environment variable with `read_api` scope
- Project path (e.g., `namespace/project-name`)
- GitLab URL (default: `https://gitlab.com`)

## Technology Choices

| Choice | Rationale                                                                     |
|--------|-------------------------------------------------------------------------------|
| **pgvector** | Single database for relational + vector data; hybrid queries; ACID compliance |
| **FastAPI** | Async, automatic OpenAPI docs, Pydantic integration                           |
| **Redis** | Fast cache, rate limiting, pub/sub for future features                        |
| **Ollama** | Local LLM for development without API costs                                   |
| **SSE** | Simpler than WebSocket and perfect unidirectional streaming                   |
| **MCP** | Standard protocol for tool integration; extensible to other services          |

## Future Considerations

- [ ] Multi-tenancy with row-level security
- [ ] Kubernetes deployment with horizontal scaling
- [ ] Observability with OpenTelemetry
