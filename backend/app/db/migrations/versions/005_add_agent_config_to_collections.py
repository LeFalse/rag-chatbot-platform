"""Add agent configuration fields to collections.

Revision ID: 005_agent_config
Revises: 004_context_chunks
Create Date: 2024-01-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005_agent_config"
down_revision: Union[str, None] = "004_context_chunks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add agent configuration columns to collections
    op.add_column(
        "collections",
        sa.Column("system_prompt", sa.Text(), nullable=True),
    )
    op.add_column(
        "collections",
        sa.Column(
            "personality",
            sa.String(50),
            nullable=True,
            server_default="professional",
        ),
    )
    op.add_column(
        "collections",
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.5"),
    )
    op.add_column(
        "collections",
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="512"),
    )
    op.add_column(
        "collections",
        sa.Column("top_k", sa.Integer(), nullable=False, server_default="5"),
    )


def downgrade() -> None:
    op.drop_column("collections", "top_k")
    op.drop_column("collections", "max_tokens")
    op.drop_column("collections", "temperature")
    op.drop_column("collections", "personality")
    op.drop_column("collections", "system_prompt")
