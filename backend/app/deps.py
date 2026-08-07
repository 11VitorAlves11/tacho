import uuid

from app.constants import DEFAULT_WORKSPACE_ID


def get_workspace_id() -> uuid.UUID:
    """Resolves the caller's workspace.

    Every recipe/category/tag is scoped to a workspace, but until v1.2 ships
    real multi-user Workspaces (see PRODUCT.md), there is only one — this
    function is the single seam to swap for an auth-derived lookup later.
    """
    return DEFAULT_WORKSPACE_ID
