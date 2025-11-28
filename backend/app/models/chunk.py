"""Chunk model for document pieces with embeddings."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgvector.sqlalchemy import Vector

from app.db.base import Base
from app.models.types import ChunkMetadata

if TYPE_CHECKING:
    from app.models.document import Document


class Chunk(Base):
    """Chunk model - document pieces with vector embeddings."""

    __tablename__ = "chunks"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),  # OpenAI ada-002 dimension, can be changed
        nullable=True,
    )
    metadata_: Mapped[ChunkMetadata] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
    )

    def __repr__(self) -> str:
        return f"<Chunk(id={self.id}, document_id={self.document_id}, index={self.chunk_index})>"
