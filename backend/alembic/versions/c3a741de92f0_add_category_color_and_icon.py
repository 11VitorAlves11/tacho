"""add category color and icon

Revision ID: c3a741de92f0
Revises: 5d7092e277e3
Create Date: 2026-09-01 17:42:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3a741de92f0"
down_revision: str | Sequence[str] | None = "5d7092e277e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("categories", sa.Column("color", sa.Text(), nullable=True))
    op.add_column("categories", sa.Column("icon", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("categories", "icon")
    op.drop_column("categories", "color")
