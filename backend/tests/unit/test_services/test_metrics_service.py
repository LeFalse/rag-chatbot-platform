"""Tests for MetricsService."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.metrics_service import MetricsService


@pytest.mark.asyncio
async def test_record_chat(session: AsyncSession):
    """Test recording a chat metric."""
    service = MetricsService(session)

    metric = await service.record_chat(
        provider="openai",
        tokens_input=100,
        tokens_output=50,
        latency_ms=1500,
        cost_usd=0.003,
    )

    assert metric.metric_type == "chat"
    assert metric.provider == "openai"
    assert metric.tokens_input == 100
    assert metric.tokens_output == 50
    assert metric.latency_ms == 1500
    assert metric.cost_usd == Decimal("0.003")


@pytest.mark.asyncio
async def test_record_embedding(session: AsyncSession):
    """Test recording an embedding metric."""
    service = MetricsService(session)

    metric = await service.record_embedding(
        provider="openai",
        tokens_used=10,
        latency_ms=100,
        cost_usd=0.0001,
    )

    assert metric.metric_type == "embedding"
    assert metric.provider == "openai"
    assert metric.tokens_input == 10
    assert metric.latency_ms == 100
    assert metric.cost_usd == Decimal("0.0001")


@pytest.mark.asyncio
async def test_record_search(session: AsyncSession):
    """Test recording a search metric."""
    service = MetricsService(session)

    metric = await service.record_search(latency_ms=50)

    assert metric.metric_type == "search"
    assert metric.provider == "pgvector"
    assert metric.latency_ms == 50
    assert metric.cost_usd is None


@pytest.mark.asyncio
async def test_get_daily_summary(session: AsyncSession):
    """Test getting daily summary of metrics."""
    service = MetricsService(session)

    # Record some metrics
    await service.record_chat(
        provider="openai",
        tokens_input=100,
        tokens_output=50,
        latency_ms=1000,
        cost_usd=0.003,
    )
    await service.record_chat(
        provider="openai",
        tokens_input=80,
        tokens_output=40,
        latency_ms=900,
        cost_usd=0.0024,
    )
    await service.record_embedding(
        provider="openai",
        tokens_used=10,
        latency_ms=100,
        cost_usd=0.0001,
    )

    # Get summary
    summary = await service.get_daily_summary(days=1)

    assert summary["period_days"] == 1
    assert "by_type" in summary
    assert "chat" in summary["by_type"]
    assert "embedding" in summary["by_type"]
    assert summary["by_type"]["chat"]["count"] == 2
    assert summary["by_type"]["embedding"]["count"] == 1
    assert summary["by_type"]["chat"]["total_tokens"] == 270
    assert float(summary["total_cost_usd"]) > 0


@pytest.mark.asyncio
async def test_get_hourly_stats(session: AsyncSession):
    """Test getting hourly statistics."""
    service = MetricsService(session)

    # Record metrics
    await service.record_chat(
        provider="ollama",
        tokens_input=100,
        tokens_output=50,
        latency_ms=1500,
    )
    await service.record_chat(
        provider="ollama",
        tokens_input=80,
        tokens_output=40,
        latency_ms=1200,
    )
    await service.record_search(latency_ms=50)

    # Get stats
    stats = await service.get_hourly_stats()

    assert stats["request_count"] == 3
    assert "latencies_by_type" in stats
    assert "chat" in stats["latencies_by_type"]
    assert "search" in stats["latencies_by_type"]
    assert stats["latencies_by_type"]["chat"]["count"] == 2
    assert stats["latencies_by_type"]["search"]["count"] == 1


@pytest.mark.asyncio
async def test_summary_by_provider(session: AsyncSession):
    """Test that summary aggregates correctly by provider."""
    service = MetricsService(session)

    # Record metrics for different providers
    await service.record_chat(
        provider="openai",
        tokens_input=100,
        tokens_output=50,
        latency_ms=1000,
        cost_usd=0.003,
    )
    await service.record_chat(
        provider="ollama",
        tokens_input=100,
        tokens_output=50,
        latency_ms=2000,
        cost_usd=0.0,
    )

    summary = await service.get_daily_summary(days=1)

    chat_stats = summary["by_type"]["chat"]
    assert chat_stats["count"] == 2
    assert "openai" in chat_stats["by_provider"]
    assert "ollama" in chat_stats["by_provider"]
    assert chat_stats["by_provider"]["openai"]["count"] == 1
    assert chat_stats["by_provider"]["ollama"]["count"] == 1
