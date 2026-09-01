import pytest
from pydantic import ValidationError

from app.schemas import CategoryCreate, CategoryUpdate


def test_category_accepts_visual_identity() -> None:
    category = CategoryCreate(name="Sobremesas", color="#E87924", icon="dessert")

    assert category.color == "#E87924"
    assert category.icon == "dessert"


@pytest.mark.parametrize("color", ["red", "#fff", "#GG0000"])
def test_category_rejects_invalid_color(color: str) -> None:
    with pytest.raises(ValidationError):
        CategoryUpdate(color=color)


def test_category_rejects_unknown_icon() -> None:
    with pytest.raises(ValidationError):
        CategoryUpdate(icon="unknown")
