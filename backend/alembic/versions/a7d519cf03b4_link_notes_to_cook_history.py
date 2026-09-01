"""link notes to cook history

Revision ID: a7d519cf03b4
Revises: f2c8a43d10e7
Create Date: 2026-09-01 17:54:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7d519cf03b4"
down_revision: str | Sequence[str] | None = "f2c8a43d10e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cook_notes", sa.Column("cook_history_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_cook_notes_cook_history_id",
        "cook_notes",
        "cook_history",
        ["cook_history_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_cook_notes_cook_history_id", "cook_notes", type_="foreignkey")
    op.drop_column("cook_notes", "cook_history_id")
