import io
from types import SimpleNamespace

import pytest
from fastapi_users.password import PasswordHelper

from scripts import reset_password as cli


def test_parse_args_requires_an_action() -> None:
    with pytest.raises(SystemExit) as exc:
        cli.parse_args([])
    assert exc.value.code == 2


def test_parse_args_rejects_list_with_email() -> None:
    with pytest.raises(SystemExit):
        cli.parse_args(["--list", "--email", "ana@example.com"])


def test_parse_args_rejects_activate_with_password_stdin() -> None:
    with pytest.raises(SystemExit):
        cli.parse_args(["--email", "ana@example.com", "--activate", "--password-stdin"])


def test_parse_args_accepts_reset_options() -> None:
    args = cli.parse_args(["--email", "ana@example.com", "--password-stdin"])
    assert args.email == "ana@example.com"
    assert args.password_stdin and not args.activate and not args.list


def test_validate_password_enforces_minimum_length() -> None:
    with pytest.raises(cli.PasswordError, match="8"):
        cli.validate_password("short")
    assert cli.validate_password("12345678") == "12345678"


def test_validate_password_requires_matching_confirmation() -> None:
    with pytest.raises(cli.PasswordError, match="coincidem"):
        cli.validate_password("password-one", "password-two")


def test_read_password_from_stdin_strips_only_the_newline() -> None:
    assert cli.read_password(True, stdin=io.StringIO(" secret pass \n")) == " secret pass "


def test_read_password_prompts_for_confirmation() -> None:
    answers = iter(["new-password", "new-password"])
    prompts: list[str] = []

    def prompt(message: str) -> str:
        prompts.append(message)
        return next(answers)

    assert cli.read_password(False, prompt=prompt) == "new-password"
    assert len(prompts) == 2


def test_hash_password_round_trips_with_fastapi_users() -> None:
    hashed = cli.hash_password("correct horse battery")
    assert "correct horse battery" not in hashed
    verified, _ = PasswordHelper().verify_and_update("correct horse battery", hashed)
    assert verified
    assert not PasswordHelper().verify_and_update("wrong", hashed)[0]


class FakeSession:
    def __init__(self, user: SimpleNamespace | None) -> None:
        self.user = user
        self.committed = False

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def commit(self) -> None:
        self.committed = True


def run_main(monkeypatch: pytest.MonkeyPatch, user: SimpleNamespace | None, argv: list[str], stdin: str = ""):
    session = FakeSession(user)
    monkeypatch.setattr(cli, "SessionLocal", lambda: session)
    monkeypatch.setattr(cli, "find_user", lambda _db, _email: session.user)
    monkeypatch.setattr(cli.sys, "stdin", io.StringIO(stdin))
    return cli.main(argv), session


def make_user() -> SimpleNamespace:
    return SimpleNamespace(email="ana@example.com", hashed_password="old", is_active=False)


def test_main_resets_password_without_printing_it(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    user = make_user()
    code, session = run_main(monkeypatch, user, ["--email", "ana@example.com", "--password-stdin"], "brand-new-pass\n")
    assert code == cli.EXIT_OK
    assert session.committed
    assert PasswordHelper().verify_and_update("brand-new-pass", user.hashed_password)[0]
    output = capsys.readouterr()
    assert "brand-new-pass" not in output.out + output.err
    assert "--activate" in output.out


def test_main_rejects_short_password_without_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    user = make_user()
    code, session = run_main(monkeypatch, user, ["--email", "ana@example.com", "--password-stdin"], "short\n")
    assert code == cli.EXIT_INVALID
    assert user.hashed_password == "old"
    assert not session.committed


def test_main_reports_unknown_email(monkeypatch: pytest.MonkeyPatch) -> None:
    code, _ = run_main(monkeypatch, None, ["--email", "nobody@example.com", "--password-stdin"], "brand-new-pass\n")
    assert code == cli.EXIT_NOT_FOUND


def test_main_activates_without_touching_the_password(monkeypatch: pytest.MonkeyPatch) -> None:
    user = make_user()
    code, session = run_main(monkeypatch, user, ["--email", "ana@example.com", "--activate"])
    assert code == cli.EXIT_OK
    assert user.is_active and user.hashed_password == "old"
    assert session.committed
