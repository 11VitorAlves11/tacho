"""add cook_notes table

Revision ID: 4d0d5fd85a2d
Revises: 2fbf5b821d94
Create Date: 2026-08-07 17:43:24.198113

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d0d5fd85a2d'
down_revision: Union[str, Sequence[str], None] = '2fbf5b821d94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # (ix_recipes_title_tsv não está nos metadados do SQLAlchemy — ver
    # migração 2fbf5b821d94 — o autogenerate volta a querer removê-lo aqui;
    # ignorado de propósito.)
    op.create_table('cook_notes',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('recipe_id', sa.UUID(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['recipe_id'], ['recipes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('cook_notes')
