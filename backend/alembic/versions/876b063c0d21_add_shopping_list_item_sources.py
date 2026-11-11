"""add shopping list item sources

Revision ID: 876b063c0d21
Revises: f6a18c7d2950
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "876b063c0d21"
down_revision: str | None = "f6a18c7d2950"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "shopping_list_item_sources",
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["shopping_list_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("item_id", "recipe_id"),
    )


def downgrade() -> None:
    op.drop_table("shopping_list_item_sources")
