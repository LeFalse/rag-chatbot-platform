"""Metric model for usage tracking."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

MetricType = Literal["chat", "embedding", "search"]


class Metric(Base):
    """Metric model - tracks usage for dashboard."""

    __tablename__ = "metrics"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    metric_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # 'chat' | 'embedding' | 'search'
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        Index("metrics_type_created_idx", "metric_type", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Metric(id={self.id}, type='{self.metric_type}')>"
