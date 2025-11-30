"""Add context_chunks column to messages.

Revision ID: 004_context_chunks
Revises: 003_embedding_dim
Create Date: 2024-01-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "004_context_chunks"
down_revision: Union[str, None] = "003_embedding_dim"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add context_chunks column to store retrieved chunks with similarity scores
    op.add_column(
        "messages",
        sa.Column("context_chunks", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "context_chunks")
