from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas import PantryItemIn


def test_pantry_item_accepts_stock_details() -> None:
    item = PantryItemIn(
        name="Farinha",
        quantity=1.5,
        unit="kg",
        expires_on=date(2027, 1, 15),
        minimum_quantity=0.5,
    )

    assert item.quantity == 1.5
    assert item.expires_on == date(2027, 1, 15)


def test_pantry_item_rejects_negative_stock() -> None:
    with pytest.raises(ValidationError):
        PantryItemIn(name="Farinha", quantity=-1)
