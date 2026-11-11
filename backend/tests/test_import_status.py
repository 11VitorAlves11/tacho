import logging
import uuid
from typing import Any

import pytest
from fastapi import HTTPException

from app.routers import recipes

WORKSPACE_ID = uuid.uuid4()
RECIPE_ID = str(uuid.uuid4())


class FakeAsyncResult:
    def __init__(self, *, state: str, result: Any = None, traceback: str | None = None) -> None:
        self.state = state
        self.result = result
        self.traceback = traceback

    def failed(self) -> bool:
        return self.state == "FAILURE"

    def ready(self) -> bool:
        return self.state in {"SUCCESS", "FAILURE"}


@pytest.fixture
def task_result(monkeypatch: pytest.MonkeyPatch):
    def install(**kwargs: Any) -> None:
        monkeypatch.setattr(recipes, "AsyncResult", lambda task_id, app=None: FakeAsyncResult(**kwargs))

    return install


def test_pending_import_reports_pending(task_result) -> None:
    task_result(state="PENDING")
    status = recipes.get_import_status("task-1", workspace_id=WORKSPACE_ID)
    assert status.status == "pending"
    assert status.recipe_id is None


def test_done_import_reveals_recipe_to_same_workspace(task_result) -> None:
    task_result(state="SUCCESS", result={"recipe_id": RECIPE_ID, "workspace_id": str(WORKSPACE_ID)})
    status = recipes.get_import_status("task-1", workspace_id=WORKSPACE_ID)
    assert status.status == "done"
    assert status.recipe_id == RECIPE_ID


def test_done_import_is_hidden_from_other_workspaces(task_result) -> None:
    task_result(state="SUCCESS", result={"recipe_id": RECIPE_ID, "workspace_id": str(WORKSPACE_ID)})
    with pytest.raises(HTTPException) as exc_info:
        recipes.get_import_status("task-1", workspace_id=uuid.uuid4())
    assert exc_info.value.status_code == 404
    assert RECIPE_ID not in str(exc_info.value.detail)


def test_legacy_string_result_is_not_revealed(task_result) -> None:
    task_result(state="SUCCESS", result=RECIPE_ID)
    with pytest.raises(HTTPException) as exc_info:
        recipes.get_import_status("task-1", workspace_id=WORKSPACE_ID)
    assert exc_info.value.status_code == 404


def test_failed_import_hides_exception_text(task_result, caplog: pytest.LogCaptureFixture) -> None:
    secret = "HTTPConnectionPool(host='internal-db.lan', port=5432): /srv/tacho/app/tasks.py"
    task_result(state="FAILURE", result=RuntimeError(secret), traceback="Traceback ...")
    with caplog.at_level(logging.ERROR, logger=recipes.logger.name), pytest.raises(HTTPException) as exc_info:
        recipes.get_import_status("task-1", workspace_id=WORKSPACE_ID)

    assert exc_info.value.status_code == 422
    assert "internal-db" not in str(exc_info.value.detail)
    assert "Falha ao importar" in str(exc_info.value.detail)
    assert secret in caplog.text
