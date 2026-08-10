import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import AuthenticationBackend, CookieTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models import User

settings = get_settings()

# Motor assíncrono próprio, só para autenticação — ver nota em
# `Settings.async_database_url` e a decisão #1 do TODO.md sobre porque
# `fastapi_users_db_sqlalchemy` não tem variante síncrona. Mesma BD do
# `Session` síncrono usado em todo o resto da app, driver diferente.
async_engine = create_async_engine(settings.async_database_url)
async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    # Sem SMTP no homelab (decisão #2 do TODO.md) — não há fluxo de
    # verificação de email nem de "esqueci-me da password" por link,
    # por isso estes tokens nunca chegam a ser enviados a lado nenhum;
    # só têm de existir para a classe base assinar os JWT internos.
    reset_password_token_secret = settings.auth_secret
    verification_token_secret = settings.auth_secret


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


cookie_transport = CookieTransport(
    cookie_name="tacho_session",
    cookie_max_age=60 * 60 * 24 * 30,  # 30 dias — uso pessoal/agregado, atrás do Authentik em produção
    cookie_secure=settings.auth_cookie_secure,
    cookie_httponly=True,
    cookie_samesite="lax",
)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.auth_secret, lifetime_seconds=60 * 60 * 24 * 30)


auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
