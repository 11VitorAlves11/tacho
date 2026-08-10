import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi_users import exceptions as fu_exceptions
from fastapi_users import schemas as fu_schemas
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas
from app.auth import UserManager, current_active_user, get_user_manager
from app.constants import DEFAULT_WORKSPACE_ID
from app.database import get_db
from app.models import User, WorkspaceMember

router = APIRouter(tags=["auth"])


@router.get("/setup/status", response_model=schemas.SetupStatus)
def setup_status(db: Session = Depends(get_db)):
    count = db.scalar(select(func.count()).select_from(User))
    return schemas.SetupStatus(needs_setup=count == 0)


@router.post("/setup", response_model=schemas.SetupStatus, status_code=201)
async def setup(
    payload: schemas.SetupRequest,
    db: Session = Depends(get_db),
    user_manager: UserManager = Depends(get_user_manager),
):
    """Cria a primeira conta e liga-a ao Workspace já semeado
    (`DEFAULT_WORKSPACE_ID`, migração `93c380aef9a6`) — nunca cria uma
    workspace nova. Só funciona enquanto não existir nenhum utilizador;
    é a única forma de entrar pela primeira vez, já que não há registo
    público nem convite por email (decisão #2 do TODO.md)."""
    count = db.scalar(select(func.count()).select_from(User))
    if count and count > 0:
        raise HTTPException(status_code=403, detail="A configuração inicial já foi concluída")
    try:
        user = await user_manager.create(fu_schemas.BaseUserCreate(email=payload.email, password=payload.password))
    except fu_exceptions.UserAlreadyExists:
        raise HTTPException(status_code=409, detail="Já existe uma conta com este email")
    db.add(WorkspaceMember(workspace_id=DEFAULT_WORKSPACE_ID, user_id=user.id))
    db.commit()
    return schemas.SetupStatus(needs_setup=False)


@router.get("/workspace/members", response_model=list[schemas.MemberOut])
def list_workspace_members(
    db: Session = Depends(get_db),
    user: User = Depends(current_active_user),
):
    rows = db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == DEFAULT_WORKSPACE_ID)
        .order_by(WorkspaceMember.joined_at)
    ).all()
    return [schemas.MemberOut(id=u.id, email=u.email, joined_at=m.joined_at) for m, u in rows]


@router.post("/workspace/members", response_model=schemas.MemberOut, status_code=201)
async def add_workspace_member(
    payload: schemas.MemberInvite,
    db: Session = Depends(get_db),
    user: User = Depends(current_active_user),
    user_manager: UserManager = Depends(get_user_manager),
):
    """Junta a segunda pessoa do agregado à mesma workspace — sem SMTP,
    sem convite por link. O dono (qualquer membro já autenticado, o Tacho
    não distingue papéis) fornece diretamente o email e a password da
    nova conta, o mesmo padrão validado no Securo
    (`app/api/workspaces.py::invite_member`), sem os extras de moeda/
    preferências/workspace pessoal automática que só fazem sentido lá."""
    try:
        new_user = await user_manager.create(
            fu_schemas.BaseUserCreate(email=payload.email, password=payload.password)
        )
    except fu_exceptions.UserAlreadyExists:
        raise HTTPException(status_code=409, detail="Já existe uma conta com este email")

    membership = WorkspaceMember(workspace_id=DEFAULT_WORKSPACE_ID, user_id=new_user.id)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return schemas.MemberOut(id=new_user.id, email=new_user.email, joined_at=membership.joined_at)
