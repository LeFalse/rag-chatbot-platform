"""Change embedding dimension from 1536 to 768.

This migration documents the change from OpenAI's text-embedding-ada-002 (1536 dimensions)
to nomic-embed-text (768 dimensions).

Revision ID: 003_embedding_dim
Revises: 002_token_tracking
Create Date: 2024-01-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "003_embedding_dim"
down_revision: Union[str, None] = "002_token_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing HNSW index
    op.drop_index("chunks_embedding_idx", table_name="chunks")

    # Change embedding column from 1536 to 768 dimensions
    # This will truncate existing embeddings - should only be run on empty database
    # or after re-generating embeddings with the new model
    op.execute("ALTER TABLE chunks DROP COLUMN embedding")
    op.execute("ALTER TABLE chunks ADD COLUMN embedding vector(768)")

    # Recreate the HNSW index for the new dimension
    op.execute(
        """
        CREATE INDEX chunks_embedding_idx ON chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    # Drop the HNSW index
    op.drop_index("chunks_embedding_idx", table_name="chunks")

    # Change embedding column back to 1536 dimensions
    op.execute("ALTER TABLE chunks DROP COLUMN embedding")
    op.execute("ALTER TABLE chunks ADD COLUMN embedding vector(1536)")

    # Recreate the HNSW index
    op.execute(
        """
        CREATE INDEX chunks_embedding_idx ON chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )
