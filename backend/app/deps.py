import uuid

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_active_user
from app.database import get_db
from app.models import User, WorkspaceMember


def get_workspace_id(
    user: User = Depends(current_active_user),
    db: Session = Depends(get_db),
) -> uuid.UUID:
    """Resolve a workspace do utilizador com sessão válida (cookie).

    O Tacho tem sempre uma única workspace por utilizador — sem troca de
    workspace nem papéis —
    por isso a primeira (e única) linha em `workspace_members` chega.
    `current_active_user` já garante 401 sem sessão válida; aqui só falta
    o caso residual de um utilizador autenticado sem membership (não
    deveria acontecer fora de dados corrompidos manualmente).
    """
    membership = db.scalars(select(WorkspaceMember).where(WorkspaceMember.user_id == user.id)).first()
    if membership is None:
        raise HTTPException(status_code=403, detail="Utilizador sem workspace associada")
    return membership.workspace_id
