"""add recipe variant origin

Revision ID: e4b973f8a21c
Revises: d9f341ac726b
Create Date: 2026-09-01 17:51:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4b973f8a21c"
down_revision: str | Sequence[str] | None = "d9f341ac726b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("recipes", sa.Column("source_recipe_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_recipes_source_recipe_id",
        "recipes",
        "recipes",
        ["source_recipe_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_recipes_source_recipe_id", "recipes", type_="foreignkey")
    op.drop_column("recipes", "source_recipe_id")
