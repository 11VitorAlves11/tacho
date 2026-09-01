"""add ingredient substitutions

Revision ID: f6a18c7d2950
Revises: e5f62a9c1847
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f6a18c7d2950"
down_revision: str | None = "e5f62a9c1847"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingredient_substitutions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ingredient_name", sa.Text(), nullable=False),
        sa.Column("substitute_name", sa.Text(), nullable=False),
        sa.Column("quantity_ratio", sa.Numeric(8, 3), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ingredient_substitutions")
