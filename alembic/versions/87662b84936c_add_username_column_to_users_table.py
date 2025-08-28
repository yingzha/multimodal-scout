"""Add username column to users table

Revision ID: 87662b84936c
Revises: a6ff9ebdf638
Create Date: 2025-08-27 18:22:15.514675

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '87662b84936c'
down_revision: Union[str, Sequence[str], None] = 'add_summary_edited_column'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add username column to users table
    op.add_column('users', sa.Column('username', sa.String(), nullable=True))
    
    # Create unique index on username (after column is added)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    
    # For existing users, we can set username to a default value like email prefix
    # This is a temporary solution - in practice you'd want to handle this differently
    op.execute("UPDATE users SET username = SPLIT_PART(email, '@', 1) || '_' || SUBSTRING(CAST(id AS TEXT), 1, 8)")
    
    # Now make username NOT NULL after setting values
    op.alter_column('users', 'username', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove username column
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_column('users', 'username')
