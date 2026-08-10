import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_users import exceptions as fu_exceptions
from fastapi_users import schemas as fu_schemas
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import schemas
from app.auth import UserManager, cookie_transport, current_active_user, get_jwt_strategy, get_user_manager
from app.config import get_settings
from app.constants import DEFAULT_WORKSPACE_ID
from app.database import get_db
from app.deps import get_workspace_id
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


@router.post("/auth/forward-login", status_code=204)
async def forward_login(
    request: Request,
    db: Session = Depends(get_db),
    user_manager: UserManager = Depends(get_user_manager),
):
    """Login silencioso quando o pedido já chega autenticado pelo forward-auth
    do Authentik (produção, atrás do NPM) — evita mostrar a página de login a
    quem o Authentik já validou (decisão do utilizador, 2026-08-10: preferir
    isto a um botão OIDC como o do Securo, que faria um segundo round-trip
    desnecessário). Só confia no header de email se vier acompanhado do
    segredo partilhado (`forward_auth_secret`, injetado só pelo NPM, nunca
    pelo Authentik em si) — sem este segredo, qualquer pedido direto ao
    backend que contornasse o NPM/Authentik (ex. outro container na mesma
    LAN) conseguia forjar o header de email e entrar como qualquer pessoa.
    Desligado por omissão (`trust_forward_auth=False`). Nunca cria conta
    nova nem workspace — só inicia sessão para quem já é membro do agregado,
    mesmo padrão fechado do resto da autenticação (decisão #2 do TODO.md);
    devolve 404 sem essa membership, para o frontend cair de volta no login
    normal por password sem expor se o email existe ou não."""
    settings = get_settings()
    if not settings.trust_forward_auth:
        raise HTTPException(status_code=404)
    if not settings.forward_auth_secret or request.headers.get("X-Tacho-Forward-Secret") != settings.forward_auth_secret:
        raise HTTPException(status_code=401, detail="Segredo de forward-auth inválido ou em falta")
    email = request.headers.get(settings.forward_auth_email_header)
    if not email:
        raise HTTPException(status_code=401, detail="Header de email do forward-auth em falta")

    try:
        user = await user_manager.get_by_email(email.lower())
    except fu_exceptions.UserNotExists:
        raise HTTPException(status_code=404, detail="Sem conta Tacho para este email")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Conta inativa")

    membership = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == DEFAULT_WORKSPACE_ID,
            WorkspaceMember.user_id == user.id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Conta sem acesso ao agregado")

    token = await get_jwt_strategy().write_token(user)
    return await cookie_transport.get_login_response(token)


@router.get("/workspace/members", response_model=list[schemas.MemberOut])
def list_workspace_members(
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
):
    rows = db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace_id)
        .order_by(WorkspaceMember.joined_at)
    ).all()
    return [schemas.MemberOut(id=u.id, email=u.email, name=u.name, joined_at=m.joined_at) for m, u in rows]


@router.post("/workspace/members", response_model=schemas.MemberOut, status_code=201)
async def add_workspace_member(
    payload: schemas.MemberInvite,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
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

    membership = WorkspaceMember(workspace_id=workspace_id, user_id=new_user.id)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return schemas.MemberOut(id=new_user.id, email=new_user.email, name=new_user.name, joined_at=membership.joined_at)


@router.delete("/workspace/members/{user_id}", status_code=204)
async def remove_workspace_member(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    workspace_id: uuid.UUID = Depends(get_workspace_id),
    current_user: User = Depends(current_active_user),
    user_manager: UserManager = Depends(get_user_manager),
):
    """Remove uma pessoa do agregado apagando a conta por completo, não só a
    linha de `workspace_members` — sem isto o email ficava reservado para
    sempre (`fastapi-users` recusa recriar conta com email já usado),
    inviabilizando corrigir um email escrito por engano ao adicionar alguém
    (decisão #5 do TODO.md). `WorkspaceMember.user_id` tem `ondelete=CASCADE`,
    por isso apagar o `User` (motor assíncrono) já resolve a membership
    sozinho, sem escrita adicional pela sessão síncrona. Recebe o `user_id`
    (não o id da linha `WorkspaceMember`) porque é isso que `MemberOut.id`
    já expõe ao frontend (`id=u.id` em `list_workspace_members`/
    `add_workspace_member` acima). Nunca permite auto-remoção — quem se
    quer ir embora usa "Sair"."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Não podes remover a tua própria conta")

    member = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.workspace_id == workspace_id,
        )
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Membro não encontrado")

    user_to_delete = await user_manager.get(user_id)
    await user_manager.delete(user_to_delete)
