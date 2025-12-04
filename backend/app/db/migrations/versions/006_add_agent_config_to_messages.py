"""Add agent_config column to messages table.

Revision ID: 006_message_agent_config
Revises: 005_agent_config
Create Date: 2024-12-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers
revision = "006_message_agent_config"
down_revision = "005_agent_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add agent_config column to messages table."""
    op.add_column(
        "messages",
        sa.Column("agent_config", JSONB, nullable=True),
    )


def downgrade() -> None:
    """Remove agent_config column from messages table."""
    op.drop_column("messages", "agent_config")
