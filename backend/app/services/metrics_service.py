"""Metrics service - tracks usage and costs."""

from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collection import Collection
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.message import Message
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

    async def get_aggregate_metrics(self) -> dict:
        """Get aggregate metrics for the dashboard.

        Returns:
            Dictionary with aggregate statistics.
        """
        # Count messages
        messages_result = await self.session.execute(
            select(func.count(Message.id))
        )
        messages_count = messages_result.scalar() or 0

        # Count documents
        documents_result = await self.session.execute(
            select(func.count(Document.id))
        )
        documents_count = documents_result.scalar() or 0

        # Count collections
        collections_result = await self.session.execute(
            select(func.count(Collection.id))
        )
        collections_count = collections_result.scalar() or 0

        # Calculate average response time from messages (assistant messages have latency)
        latency_result = await self.session.execute(
            select(func.avg(Message.latency_ms)).where(
                Message.latency_ms.isnot(None)
            )
        )
        avg_latency = latency_result.scalar()
        average_response_time_ms = round(avg_latency) if avg_latency else 0

        # Sum token usage from messages
        tokens_result = await self.session.execute(
            select(func.sum(Message.tokens_used)).where(
                Message.tokens_used.isnot(None)
            )
        )
        token_usage = tokens_result.scalar() or 0

        # Sum input tokens
        tokens_input_result = await self.session.execute(
            select(func.sum(Message.tokens_input)).where(
                Message.tokens_input.isnot(None)
            )
        )
        total_tokens_input = tokens_input_result.scalar() or 0

        # Sum output tokens
        tokens_output_result = await self.session.execute(
            select(func.sum(Message.tokens_output)).where(
                Message.tokens_output.isnot(None)
            )
        )
        total_tokens_output = tokens_output_result.scalar() or 0

        return {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "messages_count": messages_count,
            "documents_count": documents_count,
            "collections_count": collections_count,
            "average_response_time_ms": average_response_time_ms,
            "token_usage": token_usage,
            "tokens_input": total_tokens_input,
            "tokens_output": total_tokens_output,
        }

    async def get_conversations_metrics(self) -> list[dict]:
        """Get metrics for all conversations.

        Returns:
            List of conversations with their metrics.
        """
        # Get all conversations with aggregated message metrics
        query = (
            select(
                Conversation.id,
                Conversation.title,
                Conversation.created_at,
                func.count(Message.id).label("message_count"),
                func.sum(Message.tokens_input).label("tokens_input"),
                func.sum(Message.tokens_output).label("tokens_output"),
                func.avg(Message.latency_ms).label("avg_latency_ms"),
            )
            .outerjoin(Message, Conversation.id == Message.conversation_id)
            .group_by(Conversation.id)
            .order_by(Conversation.created_at.desc())
        )

        result = await self.session.execute(query)
        rows = result.fetchall()

        return [
            {
                "id": str(row.id),
                "title": row.title,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "message_count": row.message_count or 0,
                "tokens_input": row.tokens_input or 0,
                "tokens_output": row.tokens_output or 0,
                "avg_latency_ms": round(row.avg_latency_ms) if row.avg_latency_ms else 0,
            }
            for row in rows
        ]

    async def get_conversation_messages_metrics(
        self, conversation_id: UUID
    ) -> list[dict]:
        """Get metrics for all messages in a conversation.

        Args:
            conversation_id: Conversation ID.

        Returns:
            List of messages with their metrics and agent config.
        """
        # Get messages, ordering by created_at and then by role
        # (user messages should appear before assistant messages when timestamps are equal)
        role_order = case(
            (Message.role == "user", 1),
            (Message.role == "assistant", 2),
            else_=3
        )
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at, role_order)
        )

        result = await self.session.execute(query)
        messages = result.scalars().all()

        return [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "content_preview": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content,
                "prompt_input": msg.prompt_input,
                "context_chunks": msg.context_chunks,
                "tokens_input": msg.tokens_input,
                "tokens_output": msg.tokens_output,
                "tokens_used": msg.tokens_used,
                "latency_ms": msg.latency_ms,
                "model": msg.model,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                # Use the agent_config stored with the message at generation time
                "collection_config": msg.agent_config if msg.role == "assistant" else None,
            }
            for msg in messages
        ]
