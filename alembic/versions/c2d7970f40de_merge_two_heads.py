"""merge two heads

Revision ID: c2d7970f40de
Revises: 87662b84936c, a6ff9ebdf638
Create Date: 2025-08-28 02:12:56.606560

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c2d7970f40de'
down_revision: Union[str, Sequence[str], None] = ('87662b84936c', 'a6ff9ebdf638')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
