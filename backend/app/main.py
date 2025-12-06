"""RAG Chatbot Platform - FastAPI Application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.documents import router as documents_router
from app.api.routes.chat import router as chat_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.config import router as config_router

app = FastAPI(
    title="RAG Chatbot Platform",
    description="A Retrieval-Augmented Generation chatbot platform",
    version="0.1.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(metrics_router)
app.include_router(config_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RAG Chatbot Platform API",
        "docs": "/docs",
        "health": "/health",
    }
