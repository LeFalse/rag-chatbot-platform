"""Initial schema with all tables.

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Collections table
    op.create_table(
        "collections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("collection_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column(
            "metadata",
            sa.JSON(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Chunks table with vector embedding
    op.create_table(
        "chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "metadata",
            sa.JSON(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # HNSW index for vector similarity search
    op.execute(
        """
        CREATE INDEX chunks_embedding_idx ON chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )

    # Conversations table
    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("collection_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Messages table
    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Metrics table
    op.create_table(
        "metrics",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("metric_type", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Indexes for metrics
    op.create_index("metrics_created_at_idx", "metrics", ["created_at"])
    op.create_index(
        "metrics_type_created_idx", "metrics", ["metric_type", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("metrics_type_created_idx", table_name="metrics")
    op.drop_index("metrics_created_at_idx", table_name="metrics")
    op.drop_table("metrics")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_index("chunks_embedding_idx", table_name="chunks")
    op.drop_table("chunks")
    op.drop_table("documents")
    op.drop_table("collections")
    op.execute("DROP EXTENSION IF EXISTS vector")
