"""add pantry price entries

Revision ID: a436639380b8
Revises: f6a18c7d2950
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a436639380b8"
down_revision: str | None = "f6a18c7d2950"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pantry_price_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pantry_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("store", sa.Text(), nullable=True),
        sa.Column("purchased_on", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("source", sa.Text(), server_default="manual", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("source IN ('manual', 'receipt')", name="ck_pantry_price_entries_source"),
        sa.ForeignKeyConstraint(["pantry_item_id"], ["pantry_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pantry_price_entries_item_purchased_on", "pantry_price_entries", ["pantry_item_id", "purchased_on"]
    )
    op.create_index(
        "ix_pantry_price_entries_workspace_purchased_on", "pantry_price_entries", ["workspace_id", "purchased_on"]
    )


def downgrade() -> None:
    op.drop_index("ix_pantry_price_entries_workspace_purchased_on", table_name="pantry_price_entries")
    op.drop_index("ix_pantry_price_entries_item_purchased_on", table_name="pantry_price_entries")
    op.drop_table("pantry_price_entries")
