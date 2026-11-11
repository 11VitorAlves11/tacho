from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import crud, gemini, schemas
from app.config import get_settings

Upload = Callable[[], dict[str, tuple[str, bytes, str]]]


def months_ago(months: int, day: int = 10) -> date:
    today = date.today()
    index = today.year * 12 + today.month - 1 - months
    return date(index // 12, index % 12 + 1, day)


def create_item(client: TestClient, **fields: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"name": "Arroz"}
    payload.update(fields)
    response = client.post("/pantry", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def add_price(client: TestClient, item_id: str, **fields: Any) -> dict[str, Any]:
    response = client.post(f"/pantry/{item_id}/prices", json=fields)
    assert response.status_code == 201, response.text
    return response.json()


def test_price_entry_crud_and_last_price(client: TestClient) -> None:
    item = create_item(client, quantity=1, unit="kg")
    assert item["last_price"] is None

    older = add_price(client, item["id"], price=2.4, quantity=2, unit="kg", purchased_on="2025-01-05")
    assert older["unit_price"] == 1.2
    assert older["source"] == "manual"
    newer = add_price(client, item["id"], price=1.99, store="  Mercado  ")
    assert newer["purchased_on"] == date.today().isoformat()
    assert newer["store"] == "Mercado"
    assert newer["unit_price"] is None

    entries = client.get(f"/pantry/{item['id']}/prices").json()
    assert [e["id"] for e in entries] == [newer["id"], older["id"]]

    listed = client.get("/pantry").json()[0]
    assert listed["last_price"]["id"] == newer["id"]
    assert listed["last_price"]["price"] == 1.99
    patched = client.patch(f"/pantry/{item['id']}", json={"quantity": 3}).json()
    assert patched["last_price"]["id"] == newer["id"]

    assert client.delete(f"/pantry/{item['id']}/prices/{newer['id']}").status_code == 204
    assert client.delete(f"/pantry/{item['id']}/prices/{newer['id']}").status_code == 404
    assert client.get("/pantry").json()[0]["last_price"]["id"] == older["id"]


def test_deleting_item_cascades_its_prices(client: TestClient) -> None:
    item = create_item(client)
    add_price(client, item["id"], price=1)
    assert client.delete(f"/pantry/{item['id']}").status_code == 204
    assert client.get("/pantry/prices/history").json() == {"items": [], "monthly_totals": []}


@pytest.mark.parametrize(
    "payload",
    [
        {"price": -0.01},
        {"price": 1, "quantity": 0},
        {"price": 1, "quantity": -2},
        {"price": 1, "purchased_on": (date.today() + timedelta(days=5)).isoformat()},
        {"price": 1_000_000_000},
        {},
    ],
)
def test_price_entry_validation(client: TestClient, payload: dict[str, Any]) -> None:
    item = create_item(client)
    assert client.post(f"/pantry/{item['id']}/prices", json=payload).status_code == 422


def test_price_endpoints_are_workspace_scoped(client: TestClient, other_client: TestClient) -> None:
    item = create_item(client)
    entry = add_price(client, item["id"], price=3)

    assert other_client.get(f"/pantry/{item['id']}/prices").status_code == 404
    assert other_client.post(f"/pantry/{item['id']}/prices", json={"price": 1}).status_code == 404
    assert other_client.delete(f"/pantry/{item['id']}/prices/{entry['id']}").status_code == 404
    assert other_client.get("/pantry/prices/history").json() == {"items": [], "monthly_totals": []}
    assert len(client.get(f"/pantry/{item['id']}/prices").json()) == 1


def test_delete_price_entry_requires_matching_item(client: TestClient) -> None:
    rice = create_item(client)
    oil = create_item(client, name="Azeite")
    entry = add_price(client, rice["id"], price=3)
    assert client.delete(f"/pantry/{oil['id']}/prices/{entry['id']}").status_code == 404


def test_price_history_aggregates_items_and_months(client: TestClient) -> None:
    rice = create_item(client)
    oil = create_item(client, name="Azeite")
    add_price(client, rice["id"], price=2, quantity=2, purchased_on=months_ago(2, 3).isoformat())
    add_price(client, rice["id"], price=1.5, purchased_on=months_ago(2, 20).isoformat())
    add_price(client, rice["id"], price=3, quantity=2, purchased_on=months_ago(0, 1).isoformat())
    add_price(client, oil["id"], price=7.25, purchased_on=months_ago(0, 1).isoformat())
    add_price(client, oil["id"], price=100, purchased_on=months_ago(14).isoformat())

    history = client.get("/pantry/prices/history", params={"months": 12}).json()
    by_name = {series["name"]: series for series in history["items"]}
    assert list(by_name) == ["Arroz", "Azeite"]
    assert [p["price"] for p in by_name["Arroz"]["points"]] == [2, 1.5, 3]
    assert [p["unit_price"] for p in by_name["Arroz"]["points"]] == [1, None, 1.5]
    assert [p["price"] for p in by_name["Azeite"]["points"]] == [7.25]
    assert history["monthly_totals"] == [
        {"month": months_ago(2).strftime("%Y-%m"), "total": 3.5},
        {"month": months_ago(0).strftime("%Y-%m"), "total": 10.25},
    ]

    current_only = client.get("/pantry/prices/history", params={"months": 1}).json()
    assert [m["month"] for m in current_only["monthly_totals"]] == [months_ago(0).strftime("%Y-%m")]
    assert client.get("/pantry/prices/history", params={"months": 0}).status_code == 422


def test_history_window_starts_on_first_day_of_month() -> None:
    assert crud.first_day_of_window(date(2026, 3, 15), 12) == date(2025, 4, 1)
    assert crud.first_day_of_window(date(2026, 1, 31), 1) == date(2026, 1, 1)
    assert crud.first_day_of_window(date(2026, 1, 31), 13) == date(2025, 1, 1)


def test_receipt_confirm_upserts_items_and_records_prices(client: TestClient) -> None:
    existing = create_item(client, name="Leite", quantity=1, unit="L")
    client.patch(f"/pantry/{existing['id']}", json={"has_it": False})

    response = client.post(
        "/pantry/receipt/confirm",
        json={
            "store": "Mercado da Esquina",
            "purchased_on": "2026-01-15",
            "items": [
                {"name": "leite", "quantity": 6, "unit": "L", "price": 5.34},
                {"name": "Ovos", "quantity": 12, "unit": "un", "price": 2.89},
                {"name": "Sal", "price": None},
            ],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["price_entries_created"] == 2
    by_name = {item["name"]: item for item in body["items"]}
    assert set(by_name) == {"Leite", "Ovos", "Sal"}
    assert by_name["Leite"]["id"] == existing["id"]
    assert by_name["Leite"]["has_it"] is True
    assert (by_name["Leite"]["quantity"], by_name["Leite"]["unit"]) == (6, "L")
    assert by_name["Ovos"]["last_price"]["unit_price"] == pytest.approx(0.2408, abs=1e-4)
    assert by_name["Sal"]["last_price"] is None

    entries = client.get(f"/pantry/{existing['id']}/prices").json()
    assert len(entries) == 1
    assert entries[0] | {"id": None, "created_at": None, "pantry_item_id": None} == {
        "id": None,
        "created_at": None,
        "pantry_item_id": None,
        "price": 5.34,
        "quantity": 6,
        "unit": "L",
        "store": "Mercado da Esquina",
        "purchased_on": "2026-01-15",
        "source": "receipt",
        "unit_price": 0.89,
    }
    assert len(client.get("/pantry").json()) == 3


def test_receipt_confirm_validation(client: TestClient) -> None:
    assert client.post("/pantry/receipt/confirm", json={"items": []}).status_code == 422
    assert client.post("/pantry/receipt/confirm", json={"items": [{"name": "Ovos", "price": -1}]}).status_code == 422
    future = (date.today() + timedelta(days=5)).isoformat()
    payload = {"purchased_on": future, "items": [{"name": "Ovos", "price": 1}]}
    assert client.post("/pantry/receipt/confirm", json=payload).status_code == 422
    assert client.get("/pantry").json() == []


def test_read_receipt_requires_gemini(client: TestClient, png_upload: Upload, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(get_settings(), "gemini_api_key", None)
    response = client.post("/pantry/receipt", files=png_upload())
    assert response.status_code == 422
    assert response.json()["detail"] == "Leitura de fatura não está configurada (sem GEMINI_API_KEY)."


def test_read_receipt_returns_draft_without_writing(
    client: TestClient, png_upload: Upload, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "gemini_api_key", "fake-key")
    calls: list[tuple[bytes, str]] = []

    def fake_extract(_settings: Any, image: tuple[bytes, str]) -> schemas.ReceiptExtraction:
        calls.append(image)
        return schemas.ReceiptExtraction(
            store="Mercado",
            purchased_on="2026-01-15",
            items=[schemas.ReceiptLine(name="arroz", quantity=1, unit="kg", price=1.29)],
        )

    monkeypatch.setattr(gemini, "extract_receipt", fake_extract)
    response = client.post("/pantry/receipt", files=png_upload())
    assert response.status_code == 200, response.text
    assert response.json() == {
        "store": "Mercado",
        "purchased_on": "2026-01-15",
        "items": [{"name": "arroz", "quantity": 1, "unit": "kg", "price": 1.29}],
    }
    assert calls[0][1] == "image/png"
    assert client.get("/pantry").json() == []

    bad_type = client.post("/pantry/receipt", files={"file": ("a.gif", b"GIF89a", "image/gif")})
    assert bad_type.status_code == 422

    monkeypatch.setattr(gemini, "extract_receipt", lambda _settings, _image: None)
    assert client.post("/pantry/receipt", files=png_upload()).status_code == 422
