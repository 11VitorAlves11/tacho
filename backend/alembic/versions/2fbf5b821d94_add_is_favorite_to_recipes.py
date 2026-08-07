"""add is_favorite to recipes

Revision ID: 2fbf5b821d94
Revises: f8210117be6a
Create Date: 2026-08-07 17:39:08.442712

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2fbf5b821d94'
down_revision: Union[str, Sequence[str], None] = 'f8210117be6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # O índice ix_recipes_title_tsv (migração f8210117be6a) não está nos
    # metadados do SQLAlchemy — criado à mão via op.execute — por isso o
    # autogenerate tentou removê-lo aqui por engano. Mantém-se.
    op.add_column('recipes', sa.Column('is_favorite', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('recipes', 'is_favorite')
