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
│   │ API Layer │ → │  Service  │ → │ Provider  │ ────┐     │
│   │  Routes   │   │   Layer   │   │   Layer   │     │     │
│   └───────────┘   └───────────┘   └───────────┘     │     │
│                         │                           │     │
│                         ▼                           │     │
│                ┌─────────────────┐                  │     │
│                │ Repository Layer│                  │     │
│                └─────────────────┘                  │     │
└─────────────────────────┬───────────────────────────┼─────┘
                          │                           │
                          ▼                           ▼
┌───────────────────────────────────────┐   ┌───────────────┐
│              DATA LAYER               │   │    OLLAMA     │
│                                       │   │   (LLM/Emb)   │
│   ┌──────────────┐  ┌──────────────┐  │   │     + GPU     │
│   │  PostgreSQL  │  │    Redis     │  │   └───────────────┘
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

### Frontend
- **Real-time Chat**: Streaming message display
- **Document Management**: Upload, list, delete documents
- **Metrics Dashboard**: Usage, costs, cache hit rate

## Progress

### Done ✅
- Project structure and Docker Compose (with GPU support)
- FastAPI backend + React frontend
- Database models and migrations
- LLM/Embedding provider abstraction (Ollama tested)
- Cache layer (Redis: embeddings, sessions, rate limiting)
- Document processing and Chat service with RAG streaming
- API routes (documents, chat, metrics)
- Frontend pages (Chat, Documents, Dashboard)
- Token tracking, source attribution, metrics visualization

### Backlog
- Collection-specific system prompts (agent personality/restrictions)
- Agent configuration UI per collection
- Prompt templates with variables

### Ideas for Future
**RAG Improvements**
- Hybrid search (semantic + keyword)
- Chunk overlap configuration
- Re-ranking strategies
- Multi-collection queries

**Safety & Control**
- Input/output guardrails
- Topic restrictions, PII detection
- Audit logging

**Tools & Integrations**
- Tool/function calling
- Web search, calculator
- Custom tools per collection
- Webhooks

**Production**
- Authentication & multi-tenancy
- CI/CD pipeline
- Monitoring & alerting

## License

MIT
