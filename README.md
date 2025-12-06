# RAG Chatbot Platform

A Retrieval-Augmented Generation (RAG) chatbot platform built

## Overview

This platform enables you to:
- Upload documents (PDF, TXT, MD)
- Chat with your documents using AI
- Switch between LLM providers (OpenAI, Ollama)
- Monitor usage metrics and costs

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+ / FastAPI |
| Frontend | React 18 + TypeScript + Vite |
| Vector Store | PostgreSQL + pgvector |
| Cache | Redis |
| LLM | OpenAI / Ollama (abstracted) |
| Tools | MCP (Model Context Protocol) |
| Container | Docker + Docker Compose |

## Architecture

```
┌───────────────────────────────────────────────────────────┐
│                        FRONTEND                           │
│                   React + TypeScript                      │
│                                                           │
│   ┌───────────┐   ┌───────────┐   ┌───────────┐           │
│   │   Chat    │   │ Documents │   │ Dashboard │           │
│   │ Interface │   │  Upload   │   │  Metrics  │           │
│   └───────────┘   └───────────┘   └───────────┘           │
└─────────────────────────┬─────────────────────────────────┘
                          │ HTTP/SSE
                          ▼
┌───────────────────────────────────────────────────────────┐
│                        BACKEND                            │
│                   FastAPI + Python                        │
│                                                           │
│   ┌───────────┐   ┌───────────┐   ┌───────────┐           │
│   │ API Layer │ → │  Service  │ → │ Provider  │ ─────┐    │
│   │  Routes   │   │   Layer   │   │   Layer   │      │    │
│   └───────────┘   └───────────┘   └───────────┘      │    │
│                         │               │            │    │
│                         │               ▼            │    │
│                         │        ┌───────────┐       │    │
│                         │        │MCP Client │───────┼────┼───┐
│                         │        └───────────┘       │    │   │
│                         ▼                            │    │   │
│                  ┌─────────────────┐                 │    │   │
│                  │ Repository Layer│                 │    │   │
│                  └─────────────────┘                 │    │   │
└─────────────────────────┬────────────────────────────┼────┘   │
                          │                            │        │
                          ▼                            ▼        ▼
┌───────────────────────────────────────┐   ┌──────────┐  ┌──────────┐
│              DATA LAYER               │   │  OLLAMA  │  │  GitLab  │
│                                       │   │(LLM/Emb) │  │(via MCP) │
│   ┌──────────────┐  ┌──────────────┐  │   │  + GPU   │  │          │
│   │  PostgreSQL  │  │    Redis     │  │   └──────────┘  └──────────┘
│   │  + pgvector  │  │   (Cache)    │  │
│   └──────────────┘  └──────────────┘  │
└───────────────────────────────────────┘
```

## Project Structure

```
rag-chatbot-platform/
├── backend/
│   ├── app/
│   │   ├── api/              # API routes and middleware
│   │   ├── services/         # Business logic + cache
│   │   ├── providers/        # LLM and embedding abstractions
│   │   ├── mcp/              # MCP client and tool integrations
│   │   ├── repositories/     # Data access layer
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic DTOs
│   │   ├── core/             # Config, exceptions, logging
│   │   └── db/               # Database session + migrations
│   └── tests/
│       ├── unit/
│       └── integration/
│
├── frontend/
│   └── src/
│       ├── components/       # React components
│       ├── hooks/            # Custom hooks
│       ├── services/         # API client
│       └── types/            # TypeScript types
│
├── docker-compose.yml
└── .github/workflows/        # CI/CD
```

## Key Features

### Backend
- **Layered Architecture**: API → Service → Provider → Repository
- **Provider Abstraction**: Easily switch between OpenAI and Ollama
- **Caching Strategy**: Redis for embeddings, sessions, and rate limiting
- **Streaming**: SSE for real-time chat responses
- **Agent Configuration**: Per-collection personality, temperature, max_tokens, top_k
- **Language Detection**: Automatic language enforcement for LLM responses
- **MCP Integration**: Tool calling with GitLab support (search files, read code, issues, merge requests)
- **Agent Service**: Agentic loop with tool execution for LLMs that support function calling
- **Dual Mode**: Simple RAG when no MCP configured, Agent mode when MCP is enabled per collection

### Frontend
- **Real-time Chat**: Streaming message display with markdown rendering
- **Document Management**: Upload, list, delete documents and collections
- **Collection Settings**: Configure agent behavior and MCP integrations per collection
- **Metrics Dashboard**: Usage, costs, cache hit rate, agent configuration history

## Progress

### Done ✅
- Project structure and Docker Compose (with GPU support)
- FastAPI backend + React frontend
- Database models and migrations
- LLM/Embedding provider abstraction (Ollama tested)
- Cache layer (Redis: embeddings, sessions, rate limiting)
- Document processing and Chat service with RAG streaming
- API routes (documents, chat, metrics, config)
- Frontend pages (Chat, Documents, Dashboard)
- Token tracking, source attribution, metrics visualization
- Collection-specific system prompts and agent configuration
- Agent configuration UI per collection (personality, temperature, max_tokens, top_k)
- Agent config stored per message for historical tracking
- Delete collection with confirmation modal
- Language detection and automatic prefix injection for multilingual support
- MCP (Model Context Protocol) integration with GitLab
- Agent service with tool calling loop for compatible LLMs
- Config-driven max_tokens limits with API endpoint

### Ideas for Future
**RAG Improvements**
- Hybrid search (semantic + keyword)
- Chunk overlap configuration
- Re-ranking strategies
- Multi-collection queries
- Prompt templates with variables

**Safety & Control**
- Input/output guardrails
- Topic restrictions, PII detection
- Audit logging

**Tools & Integrations**
- Additional MCP servers (GitHub, Jira, Confluence)
- Web search, calculator tools
- Custom tools per collection
- Webhooks

**Production**
- Authentication & multi-tenancy
- CI/CD pipeline
- Monitoring & alerting

## License

MIT
