"""Config routes - Expose application configuration to frontend."""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("")
async def get_config():
    """Get public application configuration.

    Returns configuration values that are safe to expose to the frontend,
    such as the current LLM model name.
    """
    settings = get_settings()
    return {
        "llm_model": settings.llm_model,
        "ollama_model": settings.ollama_model,
        "embedding_model": settings.embedding_model,
        "max_tokens_default": settings.max_tokens_default,
        "max_tokens_limit": settings.max_tokens_limit,
    }
