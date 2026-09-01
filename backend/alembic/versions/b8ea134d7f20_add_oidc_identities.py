"""add oidc identities

Revision ID: b8ea134d7f20
Revises: a7d519cf03b4
Create Date: 2026-09-01 17:56:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8ea134d7f20"
down_revision: str | Sequence[str] | None = "a7d519cf03b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oidc_identities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("issuer", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issuer", "subject", name="uq_oidc_identity_issuer_subject"),
        sa.UniqueConstraint("user_id", "issuer", name="uq_oidc_identity_user_issuer"),
    )


def downgrade() -> None:
    op.drop_table("oidc_identities")
