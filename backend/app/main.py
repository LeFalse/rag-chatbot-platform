"""RAG Chatbot Platform - FastAPI Application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
