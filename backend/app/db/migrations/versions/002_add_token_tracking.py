"""Add token tracking columns to messages.

Revision ID: 002_token_tracking
Revises: 001_initial
Create Date: 2024-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_token_tracking"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add token tracking columns to messages
    op.add_column(
        "messages",
        sa.Column("tokens_input", sa.Integer(), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("tokens_output", sa.Integer(), nullable=True),
    )
    op.add_column(
        "messages",
        sa.Column("prompt_input", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "prompt_input")
    op.drop_column("messages", "tokens_output")
    op.drop_column("messages", "tokens_input")
