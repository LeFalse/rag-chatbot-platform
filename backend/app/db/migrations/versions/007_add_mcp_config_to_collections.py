"""Add MCP configuration to collections.

Revision ID: 007_mcp_config
Revises: 006_agent_config_msg
Create Date: 2025-12-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision: str = "007_mcp_config"
down_revision: Union[str, None] = "006_message_agent_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add mcp_config column to collections table.

    This column stores MCP (Model Context Protocol) configuration
    for enabling tool access (e.g., GitLab repository browsing).

    Example config:
    {
        "gitlab": {
            "enabled": true,
            "project_id": "group/project",
            "gitlab_url": "https://gitlab.com"
        }
    }
    """
    op.add_column(
        "collections",
        sa.Column("mcp_config", JSON, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("collections", "mcp_config")
