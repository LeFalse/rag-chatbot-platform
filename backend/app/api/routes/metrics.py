"""Metrics routes."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.metrics_service import MetricsService

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/daily")
async def get_daily_metrics(
    start_date: date = Query(...),
    end_date: date = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Get daily metrics summary."""
    try:
        # Calculate days from start_date to end_date
        delta = end_date - start_date
        days = delta.days + 1  # +1 to include both start and end dates

        service = MetricsService(session)
        metrics = await service.get_daily_summary(days=days)
        return [metrics]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hourly")
async def get_hourly_stats(
    start_date: date = Query(...),
    end_date: date = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """Get hourly metrics statistics."""
    try:
        service = MetricsService(session)
        stats = await service.get_hourly_stats()
        return [stats]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aggregate")
async def get_aggregate_metrics(
    session: AsyncSession = Depends(get_session),
):
    """Get aggregate metrics for dashboard."""
    try:
        service = MetricsService(session)
        metrics = await service.get_aggregate_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def get_conversations_metrics(
    session: AsyncSession = Depends(get_session),
):
    """Get metrics for all conversations."""
    try:
        service = MetricsService(session)
        metrics = await service.get_conversations_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}")
async def get_conversation_messages_metrics(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get metrics for all messages in a conversation."""
    try:
        service = MetricsService(session)
        metrics = await service.get_conversation_messages_metrics(conversation_id)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
