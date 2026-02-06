"""Add tags column to bookmarks table

Revision ID: 27901848fd2a
Revises: 69af993acf22
Create Date: 2025-12-08 19:49:26.148505

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27901848fd2a'
down_revision: Union[str, Sequence[str], None] = '69af993acf22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add tags column as JSON, nullable, with default empty array
    op.add_column('bookmarks', sa.Column('tags', sa.JSON(), nullable=True, server_default='[]'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove tags column
    op.drop_column('bookmarks', 'tags')
