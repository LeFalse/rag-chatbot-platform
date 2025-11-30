"""Metric repository for usage tracking."""

from datetime import datetime, timedelta
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric import Metric
from app.repositories.base import BaseRepository


class MetricRepository(BaseRepository[Metric]):
    """Repository for Metric model."""

    def __init__(self, session: AsyncSession):
        super().__init__(Metric, session)

    async def get_since(
        self,
        since: datetime,
        limit: int = 1000,
    ) -> Sequence[Metric]:
        """Get metrics created since a specific datetime."""
        query = select(Metric).where(Metric.created_at >= since)
        query = query.order_by(Metric.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_type(
        self,
        metric_type: str,
        since: datetime | None = None,
        limit: int = 100,
    ) -> Sequence[Metric]:
        """Get metrics by type with optional time filter."""
        query = select(Metric).where(Metric.metric_type == metric_type)

        if since:
            query = query.where(Metric.created_at >= since)

        query = query.order_by(Metric.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_summary(
        self,
        since: datetime | None = None,
    ) -> dict:
        """Get aggregated metrics summary."""
        if since is None:
            since = datetime.utcnow() - timedelta(days=30)

        # Total counts by type
        count_query = (
            select(
                Metric.metric_type,
                func.count().label("count"),
                func.sum(Metric.tokens_input).label("total_tokens_input"),
                func.sum(Metric.tokens_output).label("total_tokens_output"),
                func.avg(Metric.latency_ms).label("avg_latency"),
                func.sum(Metric.cost_usd).label("total_cost"),
            )
            .where(Metric.created_at >= since)
            .group_by(Metric.metric_type)
        )

        result = await self.session.execute(count_query)
        rows = result.fetchall()

        summary = {}
        for row in rows:
            summary[row.metric_type] = {
                "count": row.count,
                "total_tokens_input": row.total_tokens_input or 0,
                "total_tokens_output": row.total_tokens_output or 0,
                "avg_latency_ms": float(row.avg_latency) if row.avg_latency else 0,
                "total_cost_usd": float(row.total_cost) if row.total_cost else 0,
            }

        return summary

    async def get_daily_stats(
        self,
        days: int = 7,
    ) -> Sequence[dict]:
        """Get daily aggregated stats."""
        since = datetime.utcnow() - timedelta(days=days)

        query = (
            select(
                func.date_trunc("day", Metric.created_at).label("day"),
                Metric.metric_type,
                func.count().label("count"),
                func.sum(Metric.cost_usd).label("cost"),
            )
            .where(Metric.created_at >= since)
            .group_by(
                func.date_trunc("day", Metric.created_at),
                Metric.metric_type,
            )
            .order_by(func.date_trunc("day", Metric.created_at))
        )

        result = await self.session.execute(query)
        rows = result.fetchall()

        return [
            {
                "day": row.day.isoformat() if row.day else None,
                "type": row.metric_type,
                "count": row.count,
                "cost": float(row.cost) if row.cost else 0,
            }
            for row in rows
        ]
