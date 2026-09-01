"""add detailed pantry inventory

Revision ID: d9f341ac726b
Revises: c3a741de92f0
Create Date: 2026-09-01 17:46:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d9f341ac726b"
down_revision: str | Sequence[str] | None = "c3a741de92f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pantry_items", sa.Column("quantity", sa.Numeric(10, 2), nullable=True))
    op.add_column("pantry_items", sa.Column("unit", sa.Text(), nullable=True))
    op.add_column("pantry_items", sa.Column("expires_on", sa.Date(), nullable=True))
    op.add_column("pantry_items", sa.Column("minimum_quantity", sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("pantry_items", "minimum_quantity")
    op.drop_column("pantry_items", "expires_on")
    op.drop_column("pantry_items", "unit")
    op.drop_column("pantry_items", "quantity")
