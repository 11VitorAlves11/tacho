"""Fixtures partilhadas pelos testes de integração (API + base de dados).

Os testes unitários existentes não usam nenhuma destas fixtures e continuam
a correr sem base de dados. Os testes de integração precisam de um
PostgreSQL real em `DATABASE_URL` — em CI é o serviço do workflow; em local
deve apontar para uma base descartável (ver docs/development.md), porque
todas as tabelas são esvaziadas antes de cada teste. Por segurança, o nome
da base tem de conter "test".

Isolamento por TRUNCATE em vez de rollback de transação: a autenticação
(fastapi-users) usa um motor assíncrono próprio (`app/auth.py`, asyncpg)
que nunca veria dados escritos numa transação por confirmar do motor
síncrono — por isso cada pedido faz commit normalmente e a limpeza é feita
antes do teste seguinte.
"""

import io
import os
import uuid
from collections.abc import AsyncGenerator, Callable, Iterator
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from fastapi_users.password import PasswordHelper
from PIL import Image
from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from alembic import command
from alembic.config import Config
from app.constants import DEFAULT_WORKSPACE_ID

BACKEND_DIR = Path(__file__).resolve().parent.parent

OWNER_EMAIL = "owner@example.com"
OWNER_PASSWORD = "owner-password-123"
OTHER_EMAIL = "other@example.com"
OTHER_PASSWORD = "other-password-123"


@pytest.fixture(scope="session")
def database() -> Iterator[Engine]:
    """Aplica as migrações (`alembic upgrade head`) uma vez por sessão —
    numa base vazia isto valida também a cadeia completa de migrações."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.fail("DATABASE_URL must point at a disposable PostgreSQL database for the integration tests")
    if "test" not in (make_url(database_url).database or ""):
        pytest.fail("Refusing to run integration tests: the DATABASE_URL database name must contain 'test'")

    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")

    from app.database import engine

    yield engine
    engine.dispose()


def _truncate_all_tables(engine: Engine) -> None:
    with engine.begin() as connection:
        tables = connection.scalars(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version'")
        ).all()
        quoted = ", ".join(f'"{name}"' for name in tables)
        connection.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))
        # A workspace única é semeada pela migração 93c380aef9a6 — repõe-se
        # aqui porque `/setup` liga sempre a primeira conta a ela.
        connection.execute(
            text("INSERT INTO workspaces (id, name) VALUES (:id, 'Agregado')"),
            {"id": DEFAULT_WORKSPACE_ID},
        )


@pytest.fixture
def db(database: Engine) -> Iterator[Session]:
    """Base limpa (só com a workspace semeada) e uma sessão síncrona para
    preparar ou inspecionar dados diretamente."""
    _truncate_all_tables(database)
    from app.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def app(database: Engine) -> Iterator[Any]:
    """A app FastAPI com a sessão assíncrona da autenticação sem pool.

    Cada `TestClient` corre a app no seu próprio event loop; as ligações
    asyncpg ficam presas ao loop onde foram abertas, por isso a pool do
    `app.auth.async_engine` rebentaria ao reutilizar uma ligação noutro
    cliente. Com `NullPool` cada pedido abre e fecha a sua ligação."""
    from app.auth import get_async_session
    from app.config import get_settings
    from app.main import app as fastapi_app

    async_engine = create_async_engine(get_settings().async_database_url, poolclass=NullPool)
    session_maker = async_sessionmaker(async_engine, expire_on_commit=False)

    async def override_async_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    fastapi_app.dependency_overrides[get_async_session] = override_async_session
    yield fastapi_app
    fastapi_app.dependency_overrides.pop(get_async_session, None)


@pytest.fixture
def images_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """`get_settings()` é `lru_cache` — todos os módulos partilham a mesma
    instância, por isso basta alterar o atributo nela (reposto no fim do
    teste pelo monkeypatch)."""
    from app.config import get_settings

    path = tmp_path / "images"
    path.mkdir()
    monkeypatch.setattr(get_settings(), "images_dir", str(path))
    return path


def login(client: TestClient, email: str, password: str) -> None:
    response = client.post("/auth/cookie/login", data={"username": email, "password": password})
    assert response.status_code == 204, response.text
    assert "tacho_session" in client.cookies


@pytest.fixture
def anon_client(app: Any, db: Session, images_dir: Path) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


@pytest.fixture
def client(app: Any, db: Session, images_dir: Path) -> Iterator[TestClient]:
    """Primeira conta (criada por `POST /setup`, workspace semeada) com sessão iniciada."""
    with TestClient(app) as test_client:
        response = test_client.post("/setup", json={"name": "Owner", "email": OWNER_EMAIL, "password": OWNER_PASSWORD})
        assert response.status_code == 201, response.text
        login(test_client, OWNER_EMAIL, OWNER_PASSWORD)
        yield test_client


def create_workspace_user(db: Session, email: str, password: str) -> tuple[uuid.UUID, uuid.UUID]:
    """Cria uma segunda workspace com o seu próprio utilizador e membership
    diretamente na base — não existe API para isso (o Tacho só conhece uma
    workspace), mas é exatamente o cenário que o scoping por workspace tem
    de aguentar. Devolve `(workspace_id, user_id)`."""
    from app.models import User, Workspace, WorkspaceMember

    workspace = Workspace(name=f"Workspace {email}")
    user = User(
        email=email,
        hashed_password=PasswordHelper().hash(password),
        is_active=True,
        is_superuser=False,
        is_verified=True,
        name=email.split("@")[0],
    )
    db.add_all([workspace, user])
    db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id))
    db.commit()
    return workspace.id, user.id


@pytest.fixture
def other_client(app: Any, db: Session, images_dir: Path, client: TestClient) -> Iterator[TestClient]:
    """Utilizador de outra workspace, com sessão iniciada num cliente
    separado (cookies independentes de `client`)."""
    create_workspace_user(db, OTHER_EMAIL, OTHER_PASSWORD)
    with TestClient(app) as test_client:
        login(test_client, OTHER_EMAIL, OTHER_PASSWORD)
        yield test_client


@pytest.fixture
def create_recipe() -> Callable[..., dict[str, Any]]:
    """Fábrica: `create_recipe(client, title=..., ingredients=[...])` → JSON da receita criada."""

    def factory(test_client: TestClient, **fields: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {"title": "Arroz de pato", "servings": 4}
        payload.update(fields)
        response = test_client.post("/recipes", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return factory


def _png_bytes() -> bytes:
    """PNG 2x2 real, gerado pelo Pillow — os uploads são validados byte a byte
    (`app.images._load_image`), por isso um cabeçalho forjado já não chega."""
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), (67, 191, 80)).save(buffer, "PNG")
    return buffer.getvalue()


PNG_BYTES = _png_bytes()


@pytest.fixture
def png_upload() -> Callable[[], dict[str, tuple[str, bytes, str]]]:
    """Ficheiro PNG mínimo (1x1) no formato `files=` do TestClient."""

    def factory() -> dict[str, tuple[str, bytes, str]]:
        return {"file": ("foto.png", PNG_BYTES, "image/png")}

    return factory


@pytest.fixture
def login_as(app: Any) -> Iterator[Callable[[str, str], TestClient]]:
    """Fábrica: `login_as(email, password)` → novo cliente já com sessão
    iniciada (ex. para entrar com um membro recém-adicionado)."""
    with ExitStack() as stack:

        def factory(email: str, password: str) -> TestClient:
            test_client = stack.enter_context(TestClient(app))
            login(test_client, email, password)
            return test_client

        yield factory
