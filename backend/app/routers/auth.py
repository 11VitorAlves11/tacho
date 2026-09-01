import asyncio
import secrets
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi_users import exceptions as fu_exceptions
from fastapi_users import schemas as fu_schemas
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import oidc, schemas
from app.auth import (
    UserManager,
    cookie_transport,
    current_active_user,
    current_active_user_optional,
    get_jwt_strategy,
    get_user_manager,
)
from app.config import get_settings
from app.constants import DEFAULT_WORKSPACE_ID
from app.database import get_db
from app.deps import get_workspace_id
from app.models import OIDCIdentity, User, WorkspaceMember

router = APIRouter(tags=["auth"])


def _frontend_url(path: str) -> str:
    settings = get_settings()
    base = settings.public_base_url or (settings.cors_origins[0] if settings.cors_origins else "http://localhost:5173")
    return f"{base.rstrip('/')}{path}"


@router.get("/auth/oidc/status", response_model=schemas.OIDCStatus)
def oidc_status():
    settings = get_settings()
    return schemas.OIDCStatus(
        enabled=settings.oidc_enabled,
        display_name=settings.oidc_display_name,
        local_login_enabled=not settings.oidc_disable_local_login,
    )


@router.post("/auth/logout", status_code=204)
async def logout():
    return await cookie_transport.get_logout_response()


@router.get("/auth/oidc/start")
async def oidc_start(next: str = "/"):
    settings = get_settings()
    try:
        authorization_url, state_token = await asyncio.to_thread(oidc.create_authorization, settings, next)
    except (oidc.OIDCError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    response = RedirectResponse(authorization_url, status_code=302)
    response.set_cookie(
        "tacho_oidc_state",
        state_token,
        max_age=oidc.STATE_TTL_MINUTES * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
    )
    return response


@router.get("/auth/oidc/callback")
async def oidc_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
    user_manager: UserManager = Depends(get_user_manager),
    current_user: User | None = Depends(current_active_user_optional),
):
    settings = get_settings()

    def failure(message: str) -> RedirectResponse:
        response = RedirectResponse(_frontend_url(f"/login?oidc_error={quote(message)}"), status_code=302)
        response.delete_cookie("tacho_oidc_state")
        return response

    if error:
        return failure("O fornecedor cancelou ou recusou a autenticação.")
    state_token = request.cookies.get("tacho_oidc_state")
    if not code or not state or not state_token:
        return failure("Resposta OIDC incompleta.")
    try:
        state_payload = oidc.decode_state(settings, state_token, state)
        tokens = await asyncio.to_thread(oidc.exchange_code, settings, code, state_payload["verifier"])
        claims = await asyncio.to_thread(oidc.validate_id_token, settings, tokens["id_token"], state_payload["nonce"])
    except (oidc.OIDCError, OSError, KeyError) as exc:
        return failure(str(exc))

    issuer = settings.oidc_issuer.rstrip("/") if settings.oidc_issuer else ""
    subject = str(claims["sub"])
    identity = db.scalar(select(OIDCIdentity).where(OIDCIdentity.issuer == issuer, OIDCIdentity.subject == subject))
    user: User | None = identity.user if identity else None

    if user is None and current_user is not None:
        already_linked = db.scalar(
            select(OIDCIdentity).where(OIDCIdentity.user_id == current_user.id, OIDCIdentity.issuer == issuer)
        )
        if already_linked is not None:
            return failure("Esta conta local já está associada a outra identidade deste fornecedor.")
        identity = OIDCIdentity(
            user_id=current_user.id,
            issuer=issuer,
            subject=subject,
            email=claims.get("email"),
        )
        db.add(identity)
        db.commit()
        user = current_user

    if user is None and settings.oidc_allow_provisioning:
        email = claims.get("email")
        if not email or claims.get("email_verified") is False:
            return failure("O fornecedor não devolveu um email verificado.")
        existing = db.scalar(select(User).where(func.lower(User.email) == str(email).lower()))
        if existing is not None:
            return failure("Já existe uma conta com este email. Entra localmente e associa o OIDC no menu da conta.")
        try:
            created = await user_manager.create(
                fu_schemas.BaseUserCreate(email=email, password=secrets.token_urlsafe(48))
            )
        except fu_exceptions.UserAlreadyExists:
            return failure("Já existe uma conta com este email.")
        user = db.get(User, created.id)
        if user is None:
            return failure("Não foi possível concluir o provisionamento OIDC.")
        user.name = claims.get("name") or claims.get("preferred_username")
        db.add(WorkspaceMember(workspace_id=DEFAULT_WORKSPACE_ID, user_id=user.id))
        db.add(OIDCIdentity(user_id=user.id, issuer=issuer, subject=subject, email=email))
        db.commit()

    if user is None:
        return failure("Identidade não associada. Entra com password e associa o OIDC no menu da conta.")
    if not user.is_active:
        return failure("Esta conta está inativa.")
    membership = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == DEFAULT_WORKSPACE_ID,
            WorkspaceMember.user_id == user.id,
        )
    )
    if membership is None:
        return failure("Esta conta não tem acesso ao agregado.")

    token = await get_jwt_strategy().write_token(user)
    login_response = await cookie_transport.get_login_response(token)
    response = RedirectResponse(_frontend_url(str(state_payload.get("next", "/"))), status_code=302)
    for header in login_response.headers.getlist("set-cookie"):
        response.headers.append("set-cookie", header)
    response.delete_cookie("tacho_oidc_state")
    return response


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
    público nem convite por email."""
    count = db.scalar(select(func.count()).select_from(User))
    if count and count > 0:
        raise HTTPException(status_code=403, detail="A configuração inicial já foi concluída")
    try:
        user = await user_manager.create(fu_schemas.BaseUserCreate(email=payload.email, password=payload.password))
    except fu_exceptions.UserAlreadyExists:
        raise HTTPException(status_code=409, detail="Já existe uma conta com este email")
    created_user = db.get(User, user.id)
    if created_user is None:
        raise HTTPException(status_code=500, detail="Não foi possível concluir a criação da conta")
    created_user.name = payload.name.strip()
    db.add(WorkspaceMember(workspace_id=DEFAULT_WORKSPACE_ID, user_id=user.id))
    db.commit()
    return schemas.SetupStatus(needs_setup=False)


@router.post("/auth/forward-login", status_code=204)
async def forward_login(
    request: Request,
    db: Session = Depends(get_db),
    user_manager: UserManager = Depends(get_user_manager),
):
    """Login silencioso quando o pedido já chega autenticado por um proxy
    forward-auth — evita mostrar a página de login a quem o proxy já validou.
    Só confia no header de email se vier acompanhado do segredo partilhado
    (`forward_auth_secret`, injetado só pelo proxy) — sem este segredo,
    qualquer pedido direto ao backend que contornasse o proxy conseguiria
    forjar a identidade e entrar como qualquer pessoa.
    Desligado por omissão (`trust_forward_auth=False`). Nunca cria conta nova
    nem workspace — só inicia sessão para quem já é membro do workspace.
    `detail` é sempre um dict com `reason` — o frontend usa esse código
    para distinguir "forward-auth nem se aplica aqui" (desligado,
    segredo/header em falta — cai em silêncio no login normal) de "o
    proxy já identificou esta pessoa mas falta ação do administrador"
    (`no_account`/`inactive`/`no_membership` — mostra uma página de erro
    dedicada em vez do login, porque não faz sentido pedir password de uma
    conta que não existe."""
    settings = get_settings()
    if not settings.trust_forward_auth:
        raise HTTPException(status_code=404, detail={"reason": "disabled"})
    if (
        not settings.forward_auth_secret
        or request.headers.get("X-Tacho-Forward-Secret") != settings.forward_auth_secret
    ):
        raise HTTPException(status_code=401, detail={"reason": "bad_secret"})
    email = request.headers.get(settings.forward_auth_email_header)
    if not email:
        raise HTTPException(status_code=401, detail={"reason": "no_email_header"})

    try:
        user = await user_manager.get_by_email(email.lower())
    except fu_exceptions.UserNotExists:
        raise HTTPException(status_code=404, detail={"reason": "no_account", "email": email})
    if not user.is_active:
        raise HTTPException(status_code=403, detail={"reason": "inactive", "email": email})

    membership = db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == DEFAULT_WORKSPACE_ID,
            WorkspaceMember.user_id == user.id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail={"reason": "no_membership", "email": email})

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
        new_user = await user_manager.create(fu_schemas.BaseUserCreate(email=payload.email, password=payload.password))
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
    inviabilizando corrigir um email escrito por engano ao adicionar alguém.
    `WorkspaceMember.user_id` tem `ondelete=CASCADE`,
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
