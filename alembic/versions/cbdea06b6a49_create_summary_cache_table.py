"""Create summary_cache table

Revision ID: cbdea06b6a49
Revises: 
Create Date: 2025-08-06 21:41:46.344374

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cbdea06b6a49'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'summary_cache',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_summary_cache_url', 'summary_cache', ['url'], unique=True)
    op.create_index('ix_summary_cache_created_at', 'summary_cache', ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_summary_cache_created_at', table_name='summary_cache')
    op.drop_index('ix_summary_cache_url', table_name='summary_cache')
    op.drop_table('summary_cache')
