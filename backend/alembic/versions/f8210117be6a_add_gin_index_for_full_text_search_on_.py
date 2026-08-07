"""add gin index for full text search on recipe title

Revision ID: f8210117be6a
Revises: d55bbdb8e942
Create Date: 2026-08-07 17:37:29.417216

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8210117be6a'
down_revision: Union[str, Sequence[str], None] = 'd55bbdb8e942'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "CREATE INDEX ix_recipes_title_tsv ON recipes "
        "USING gin (to_tsvector('portuguese', title))"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX ix_recipes_title_tsv")
