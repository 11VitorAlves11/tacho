"""seed default workspace

Revision ID: 93c380aef9a6
Revises: 4a247ab344f6
Create Date: 2026-08-06 22:08:52.055341

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '93c380aef9a6'
down_revision: Union[str, Sequence[str], None] = '4a247ab344f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Fixed on purpose: until multi-user Workspaces ship (v1.2), every recipe
# belongs to this single seeded workspace. See app.constants.DEFAULT_WORKSPACE_ID.
DEFAULT_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

workspaces = sa.table(
    "workspaces",
    sa.column("id", UUID(as_uuid=True)),
    sa.column("name", sa.Text),
)


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(workspaces, [{"id": DEFAULT_WORKSPACE_ID, "name": "Agregado"}])


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(sa.text("DELETE FROM workspaces WHERE id = :id").bindparams(id=str(DEFAULT_WORKSPACE_ID)))
