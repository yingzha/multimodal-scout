"""Migrate auth to Firebase: drop password_hash, add firebase_uid

Revision ID: a1b2c3d4e5f6
Revises: 27901848fd2a
Create Date: 2026-02-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '51971e4fffe8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('users', 'password_hash')
    op.add_column('users', sa.Column('firebase_uid', sa.String(), nullable=True))
    op.create_unique_constraint('uq_users_firebase_uid', 'users', ['firebase_uid'])
    op.create_index('ix_users_firebase_uid', 'users', ['firebase_uid'])


def downgrade() -> None:
    op.drop_index('ix_users_firebase_uid', table_name='users')
    op.drop_constraint('uq_users_firebase_uid', 'users', type_='unique')
    op.drop_column('users', 'firebase_uid')
    op.add_column('users', sa.Column('password_hash', sa.String(), nullable=True))
