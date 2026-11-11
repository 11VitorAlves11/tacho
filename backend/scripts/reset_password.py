"""Recuperação de acesso para quem administra a instalação.

O Tacho não envia emails, por isso não há "esqueci-me da password" por link.
Este comando corre dentro do container e altera a conta diretamente na BD:

    docker compose exec web python -m scripts.reset_password --list
    docker compose exec web python -m scripts.reset_password --email ana@example.com
    docker compose exec web python -m scripts.reset_password --email ana@example.com --activate

Códigos de saída: 0 sucesso, 1 conta inexistente, 2 argumentos ou password
inválidos, 130 cancelado.
"""

from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from fastapi_users.password import PasswordHelper  # noqa: E402
from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.constants import DEFAULT_WORKSPACE_ID  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import User, WorkspaceMember  # noqa: E402

# Igual a `schemas.SetupRequest.password` — o mínimo exigido na criação da conta.
MIN_PASSWORD_LENGTH = 8

EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_INVALID = 2
EXIT_CANCELLED = 130


class PasswordError(ValueError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.reset_password",
        description="Redefine a password de uma conta local do Tacho, ou reativa-a.",
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--email", help="email da conta a alterar")
    action.add_argument("--list", action="store_true", help="lista as contas existentes")
    parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="lê a nova password da primeira linha do stdin em vez de a pedir",
    )
    parser.add_argument(
        "--activate",
        action="store_true",
        help="só marca a conta como ativa, sem alterar a password",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list and (args.password_stdin or args.activate):
        parser.error("--list não se combina com --password-stdin nem --activate")
    if args.activate and args.password_stdin:
        parser.error("--activate não altera a password; não uses --password-stdin")
    return args


def validate_password(password: str, confirmation: str | None = None) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordError(f"A password tem de ter pelo menos {MIN_PASSWORD_LENGTH} caracteres.")
    if confirmation is not None and password != confirmation:
        raise PasswordError("As passwords não coincidem.")
    return password


def read_password(
    from_stdin: bool,
    stdin: TextIO | None = None,
    prompt: Callable[[str], str] = getpass.getpass,
) -> str:
    if from_stdin:
        return validate_password((stdin or sys.stdin).readline().rstrip("\r\n"))
    password = prompt("Nova password: ")
    return validate_password(password, prompt("Confirmar password: "))


def hash_password(password: str) -> str:
    """Mesmo algoritmo do `UserManager` (PasswordHelper por omissão do fastapi-users)."""
    return PasswordHelper().hash(password)


def find_user(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.strip().lower()))


def print_users(db: Session) -> None:
    rows = db.execute(
        select(User, WorkspaceMember.user_id.is_not(None))
        .outerjoin(
            WorkspaceMember,
            (WorkspaceMember.user_id == User.id) & (WorkspaceMember.workspace_id == DEFAULT_WORKSPACE_ID),
        )
        .order_by(User.email)
    ).all()
    if not rows:
        print("Ainda não existe nenhuma conta.")
        return
    print(f"{'EMAIL':<40} {'NOME':<24} {'ATIVA':<6} MEMBRO")
    for user, is_member in rows:
        active = "sim" if user.is_active else "não"
        member = "sim" if is_member else "não"
        print(f"{user.email:<40} {(user.name or '-'):<24} {active:<6} {member}")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    with SessionLocal() as db:
        if args.list:
            print_users(db)
            return EXIT_OK

        user = find_user(db, args.email)
        if user is None:
            print(f"Não existe nenhuma conta com o email {args.email}.", file=sys.stderr)
            return EXIT_NOT_FOUND

        if args.activate:
            user.is_active = True
            db.commit()
            print(f"Conta {user.email} ativada.")
            return EXIT_OK

        try:
            password = read_password(args.password_stdin)
        except PasswordError as exc:
            print(exc, file=sys.stderr)
            return EXIT_INVALID
        except (EOFError, KeyboardInterrupt):
            print("\nCancelado; nada foi alterado.", file=sys.stderr)
            return EXIT_CANCELLED

        user.hashed_password = hash_password(password)
        db.commit()
        print(f"Password de {user.email} alterada.")
        if not user.is_active:
            print("Aviso: a conta está inativa; usa --activate para a reativar.")
        return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
