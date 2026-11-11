"""merge shopping list sources and pantry prices

Revision ID: 7607cd37284c
Revises: 876b063c0d21, a436639380b8

Ponto de junção das duas migrações criadas em paralelo a partir de
f6a18c7d2950 (`shopping_list_item_sources` e `pantry_price_entries`); não
altera o esquema.
"""

from collections.abc import Sequence

revision: str = "7607cd37284c"
down_revision: tuple[str, str] = ("876b063c0d21", "a436639380b8")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
