"""Reversibilidade de migrações: desce até antes de uma revisão e volta a
`head` sobre a base de testes (já migrada pela fixture `database`)."""

from pathlib import Path

from sqlalchemy import Engine, inspect

from alembic import command
from alembic.config import Config

ALEMBIC_DIR = Path(__file__).resolve().parent.parent / "alembic"


def test_shopping_list_item_sources_migration_is_reversible(database: Engine) -> None:
    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))

    command.downgrade(config, "876b063c0d21-1")
    try:
        assert "shopping_list_item_sources" not in inspect(database).get_table_names()
    finally:
        command.upgrade(config, "head")

    assert "shopping_list_item_sources" in inspect(database).get_table_names()
