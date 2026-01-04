"""add_index_to_source_link_for_deduplication

Revision ID: 51971e4fffe8
Revises: 27901848fd2a
Create Date: 2026-01-04 12:06:45.137355

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51971e4fffe8'
down_revision: Union[str, Sequence[str], None] = '27901848fd2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add index to source_link for efficient cross-source deduplication queries."""
    op.create_index('ix_sources_source_link', 'sources', ['source_link'])


def downgrade() -> None:
    """Remove source_link index."""
    op.drop_index('ix_sources_source_link', table_name='sources')
