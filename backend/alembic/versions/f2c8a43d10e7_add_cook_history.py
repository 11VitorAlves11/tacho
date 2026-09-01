"""add cook history

Revision ID: f2c8a43d10e7
Revises: e4b973f8a21c
Create Date: 2026-09-01 17:53:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2c8a43d10e7"
down_revision: str | Sequence[str] | None = "e4b973f8a21c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cook_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("recipe_id", sa.UUID(), nullable=False),
        sa.Column("made_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute(
        """INSERT INTO cook_history (id, recipe_id, made_at)
        SELECT gen_random_uuid(), id, last_made_at FROM recipes WHERE last_made_at IS NOT NULL"""
    )


def downgrade() -> None:
    op.drop_table("cook_history")
