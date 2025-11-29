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
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│                    React + TypeScript                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │    Chat     │  │  Documents  │  │  Dashboard  │              │
│  │  Interface  │  │   Upload    │  │   Metrics   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP/SSE
┌──────────────────────────▼──────────────────────────────────────┐
│                         BACKEND                                  │
│                    FastAPI + Python                              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  API Layer  │→ │   Service   │→ │  Provider   │              │
│  │   Routes    │  │    Layer    │  │   Layer     │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                           │                      │
│                    ┌──────────────────────┼──────────────────┐  │
│                    │     Repository Layer │                  │  │
│                    └──────────────────────┼──────────────────┘  │
└──────────────────────────┬────────────────┼─────────────────────┘
                           │                │
┌──────────────────────────▼──────────────────────────────────────┐
│                      DATA LAYER                                  │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │    PostgreSQL    │    │      Redis       │                   │
│  │    + pgvector    │    │     (Cache)      │                   │
│  └──────────────────┘    └──────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
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

## Development Roadmap

- [x] Project structure setup
- [x] Docker Compose configuration
- [x] FastAPI backend with health check
- [x] React frontend setup
- [x] Database models and migrations
- [x] LLM provider abstraction
- [x] Embedding provider abstraction
- [x] Cache layer (Redis)
- [x] Document processing service
- [x] Chat service with RAG
- [ ] API routes
- [ ] Frontend components
- [ ] CI/CD pipeline

## License

MIT
