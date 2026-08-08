"""add duration_minutes to steps

Revision ID: ab0f3fc87c29
Revises: 4d0d5fd85a2d
Create Date: 2026-08-08 20:54:23.113795

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab0f3fc87c29'
down_revision: Union[str, Sequence[str], None] = '4d0d5fd85a2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('steps', sa.Column('duration_minutes', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('steps', 'duration_minutes')
