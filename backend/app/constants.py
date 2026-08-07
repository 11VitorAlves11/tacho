import uuid

# Matches alembic/versions/93c380aef9a6_seed_default_workspace.py.
# Until multi-user Workspaces ship (v1.2), every recipe belongs to this
# single seeded workspace.
DEFAULT_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
