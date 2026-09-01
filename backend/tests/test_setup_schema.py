import pytest
from pydantic import ValidationError

from app.schemas import SetupRequest


def test_setup_request_normalizes_name() -> None:
    request = SetupRequest(name="  Maria Silva  ", email="maria@example.com", password="password-segura")

    assert request.name == "Maria Silva"


@pytest.mark.parametrize("name", ["", " ", " a "])
def test_setup_request_rejects_short_name_after_trimming(name: str) -> None:
    with pytest.raises(ValidationError):
        SetupRequest(name=name, email="maria@example.com", password="password-segura")


def test_setup_request_requires_eight_character_password() -> None:
    with pytest.raises(ValidationError):
        SetupRequest(name="Maria", email="maria@example.com", password="curta")
