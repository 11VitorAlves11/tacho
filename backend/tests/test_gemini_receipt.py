from datetime import date

import pytest

from app import gemini, schemas
from app.config import get_settings


@pytest.fixture
def settings_with_key(monkeypatch: pytest.MonkeyPatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "gemini_api_key", "fake-key")
    return settings


def test_extract_receipt_without_key_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "gemini_api_key", None)
    assert gemini.extract_receipt(get_settings(), (b"\x89PNG", "image/png")) is None


@pytest.mark.parametrize("image", [(b"", "image/png"), (b"GIF89a", "image/gif"), (b"%PDF", "application/pdf")])
def test_extract_receipt_rejects_invalid_images_before_calling_gemini(
    settings_with_key, monkeypatch: pytest.MonkeyPatch, image: tuple[bytes, str]
) -> None:
    def fail(*_args, **_kwargs):
        raise AssertionError("Gemini must not be called")

    monkeypatch.setattr(gemini, "_extract", fail)
    assert gemini.extract_receipt(settings_with_key, image) is None


def test_clean_receipt_drops_impossible_values() -> None:
    raw = schemas.ReceiptExtraction(
        store="  ",
        purchased_on="2026-02-30",
        items=[
            schemas.ReceiptLine(name=" arroz ", quantity=0, unit=" kg ", price=-1),
            schemas.ReceiptLine(name="  ", price=2),
            schemas.ReceiptLine(name="ovos", quantity=12, unit="un", price=2.89),
        ],
    )
    cleaned = gemini._clean_receipt(raw, date(2026, 3, 1))
    assert cleaned.store is None
    assert cleaned.purchased_on is None
    assert cleaned.items == [
        schemas.ReceiptLine(name="arroz", quantity=None, unit="kg", price=None),
        schemas.ReceiptLine(name="ovos", quantity=12, unit="un", price=2.89),
    ]


def test_clean_receipt_keeps_valid_dates_and_rejects_future_ones() -> None:
    valid = schemas.ReceiptExtraction(store="Mercado", purchased_on="2026-02-28")
    assert gemini._clean_receipt(valid, date(2026, 3, 1)).purchased_on == "2026-02-28"
    future = schemas.ReceiptExtraction(purchased_on="2026-03-02")
    assert gemini._clean_receipt(future, date(2026, 3, 1)).purchased_on is None
