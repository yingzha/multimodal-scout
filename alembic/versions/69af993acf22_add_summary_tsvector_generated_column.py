"""add_summary_tsvector_generated_column

Revision ID: 69af993acf22
Revises: 60600a482e3c
Create Date: 2025-09-10 22:31:58.218706

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69af993acf22'
down_revision: Union[str, Sequence[str], None] = '60600a482e3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add the generated tsvector column for full-text search
    op.execute("""
        ALTER TABLE sources 
        ADD COLUMN summary_tsvector tsvector 
        GENERATED ALWAYS AS (to_tsvector('english', COALESCE(summary, ''))) STORED
    """)
    
    # Create GIN index for fast full-text search
    op.execute("""
        CREATE INDEX idx_sources_summary_fts 
        ON sources USING GIN (summary_tsvector)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the index first
    op.execute("DROP INDEX IF EXISTS idx_sources_summary_fts")
    
    # Drop the generated column
    op.execute("ALTER TABLE sources DROP COLUMN IF EXISTS summary_tsvector")
