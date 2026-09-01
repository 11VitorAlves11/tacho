"""add meal plan recurrences

Revision ID: d4fe28a7b901
Revises: c91a50ed6382
Create Date: 2026-09-01 18:02:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4fe28a7b901"
down_revision: str | Sequence[str] | None = "c91a50ed6382"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meal_plan_recurrences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("recipe_id", sa.UUID(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("meal_type", sa.Text(), nullable=False),
        sa.Column("interval_weeks", sa.Integer(), server_default="1", nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_meal_plan_recurrence_weekday"),
        sa.CheckConstraint("interval_weeks >= 1", name="ck_meal_plan_recurrence_interval"),
        sa.ForeignKeyConstraint(["recipe_id"], ["recipes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("meal_plan_recurrences")
