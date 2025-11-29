"""Metrics service - tracks usage and costs."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric import Metric
from app.repositories.metric_repo import MetricRepository


class MetricsService:
    """Service for tracking API usage and costs."""

    def __init__(self, session: AsyncSession):
        """Initialize service with database session.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session
        self.repo = MetricRepository(session)

    async def record_chat(
        self,
        provider: str,
        tokens_input: int,
        tokens_output: int,
        latency_ms: int,
        cost_usd: float | None = None,
    ) -> Metric:
        """Record a chat API call.

        Args:
            provider: LLM provider name (e.g., 'openai', 'ollama').
            tokens_input: Input tokens used.
            tokens_output: Output tokens used.
            latency_ms: Response time in milliseconds.
            cost_usd: Cost in USD (if applicable).

        Returns:
            Created Metric record.
        """
        metric = Metric(
            metric_type="chat",
            provider=provider,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
            cost_usd=Decimal(str(cost_usd)) if cost_usd else None,
        )

        self.session.add(metric)
        await self.session.flush()

        return metric

    async def record_embedding(
        self,
        provider: str,
        tokens_used: int,
        latency_ms: int,
        cost_usd: float | None = None,
    ) -> Metric:
        """Record an embedding API call.

        Args:
            provider: Embedding provider name.
            tokens_used: Tokens used.
            latency_ms: Response time in milliseconds.
            cost_usd: Cost in USD (if applicable).

        Returns:
            Created Metric record.
        """
        metric = Metric(
            metric_type="embedding",
            provider=provider,
            tokens_input=tokens_used,
            tokens_output=0,
            latency_ms=latency_ms,
            cost_usd=Decimal(str(cost_usd)) if cost_usd else None,
        )

        self.session.add(metric)
        await self.session.flush()

        return metric

    async def record_search(
        self,
        latency_ms: int,
    ) -> Metric:
        """Record a vector search operation.

        Args:
            latency_ms: Search latency in milliseconds.

        Returns:
            Created Metric record.
        """
        metric = Metric(
            metric_type="search",
            provider="pgvector",
            tokens_input=0,
            tokens_output=0,
            latency_ms=latency_ms,
            cost_usd=None,
        )

        self.session.add(metric)
        await self.session.flush()

        return metric

    async def get_daily_summary(
        self,
        days: int = 1,
    ) -> dict:
        """Get usage summary for the last N days.

        Args:
            days: Number of days to summarize.

        Returns:
            Dictionary with usage statistics.
        """
        since = datetime.utcnow() - timedelta(days=days)
        metrics = await self.repo.get_since(since)

        # Aggregate by metric type
        by_type: dict[str, dict] = {}
        total_cost = Decimal("0")

        for metric in metrics:
            metric_type = metric.metric_type
            if metric_type not in by_type:
                by_type[metric_type] = {
                    "count": 0,
                    "total_tokens": 0,
                    "avg_latency_ms": 0,
                    "total_cost": Decimal("0"),
                    "by_provider": {},
                }

            type_stats = by_type[metric_type]
            type_stats["count"] += 1
            type_stats["total_tokens"] += (
                metric.tokens_input + metric.tokens_output
            )
            if metric.cost_usd:
                type_stats["total_cost"] += metric.cost_usd
                total_cost += metric.cost_usd

            # Aggregate by provider
            provider = metric.provider or "unknown"
            if provider not in type_stats["by_provider"]:
                type_stats["by_provider"][provider] = {
                    "count": 0,
                    "total_cost": Decimal("0"),
                }

            type_stats["by_provider"][provider]["count"] += 1
            if metric.cost_usd:
                type_stats["by_provider"][provider]["total_cost"] += (
                    metric.cost_usd
                )

        return {
            "period_days": days,
            "total_cost_usd": float(total_cost),
            "by_type": {
                k: {
                    **v,
                    "total_cost": float(v["total_cost"]),
                    "by_provider": {
                        pk: {
                            **pv,
                            "total_cost": float(pv["total_cost"]),
                        }
                        for pk, pv in v["by_provider"].items()
                    },
                }
                for k, v in by_type.items()
            },
        }

    async def get_hourly_stats(self) -> dict:
        """Get stats for the last hour.

        Returns:
            Dictionary with hourly statistics.
        """
        since = datetime.utcnow() - timedelta(hours=1)
        metrics = await self.repo.get_since(since)

        total_latency = 0
        count = 0
        latencies_by_type: dict[str, list[int]] = {}

        for metric in metrics:
            count += 1
            total_latency += metric.latency_ms
            metric_type = metric.metric_type
            if metric_type not in latencies_by_type:
                latencies_by_type[metric_type] = []
            latencies_by_type[metric_type].append(metric.latency_ms)

        avg_latency = total_latency / count if count > 0 else 0

        return {
            "request_count": count,
            "avg_latency_ms": avg_latency,
            "latencies_by_type": {
                metric_type: {
                    "count": len(latencies),
                    "avg_ms": sum(latencies) / len(latencies),
                    "min_ms": min(latencies),
                    "max_ms": max(latencies),
                }
                for metric_type, latencies in latencies_by_type.items()
            },
        }
