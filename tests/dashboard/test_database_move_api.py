"""Changing the Database's location over real HTTP, with a stand-in folder
picker and a temporary `.env` (Issue #198, ADR-0030)."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from dashboard.folder_picker import FolderPickerError

ENV = "# mine\nDATABASE_PATH= .data/budget.db\nBEEM_USERNAME=nathan\n"


def call(server, method: str, path: str, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    request = Request(f"http://127.0.0.1:{server.server_port}{path}", data=body, method=method)
    with urlopen(request) as response:
        return response.status, json.loads(response.read())


def failure(server, method: str, path: str, payload=None):
    with pytest.raises(HTTPError) as caught:
        call(server, method, path, payload)
    return caught.value.code, json.loads(caught.value.read())["error"]


@pytest.fixture
def env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", "original")
    path = tmp_path / ".env"
    path.write_text(ENV, encoding="utf-8")
    return path


@pytest.fixture
def new_folder(tmp_path: Path):
    folder = tmp_path / "new"
    folder.mkdir()
    return folder


def test_choosing_an_empty_folder_reports_that_the_database_will_be_moved(serve, store, env, new_folder):
    server = serve(store, env_path=env, pick_folder=lambda: str(new_folder))

    status, body = call(server, "POST", "/api/database/choose-folder")

    assert status == 200
    assert body == {
        "cancelled": False,
        "folder": str(new_folder.resolve()),
        "outcome": "move",
        "target": str(new_folder.resolve() / "budget.db"),
    }
    assert env.read_text(encoding="utf-8") == ENV  # choosing changes nothing


def test_cancelling_the_dialog_is_not_an_error(serve, store, env):
    server = serve(store, env_path=env, pick_folder=lambda: None)

    assert call(server, "POST", "/api/database/choose-folder") == (200, {"cancelled": True})


def test_a_picker_that_cannot_open_is_reported_as_an_error(serve, store, env):
    def broken():
        raise FolderPickerError("No display")

    server = serve(store, env_path=env, pick_folder=broken)

    assert failure(server, "POST", "/api/database/choose-folder") == (500, "No display")


def test_a_chosen_folder_that_cannot_be_used_is_reported(serve, store, env, tmp_path):
    server = serve(store, env_path=env, pick_folder=lambda: str(tmp_path / "gone"))

    status, message = failure(server, "POST", "/api/database/choose-folder")

    assert status == 400
    assert "isn't a folder" in message


def test_confirming_a_move_serves_the_same_data_from_the_new_folder_without_a_restart(
    serve, store, env, new_folder, tmp_path
):
    store.write_settings({"currency": "GBP"})
    server = serve(store, env_path=env)

    status, body = call(server, "POST", "/api/database/location", {"folder": str(new_folder)})

    moved = new_folder.resolve() / "budget.db"
    assert status == 200
    assert body["path"] == str(moved)
    assert call(server, "GET", "/api/database")[1]["path"] == str(moved)
    assert call(server, "GET", "/api/settings")[1]["currency"] == "GBP"
    assert not (tmp_path / "budget.db").exists()
    assert env.read_text(encoding="utf-8") == f"# mine\nDATABASE_PATH={moved}\nBEEM_USERNAME=nathan\n"
    assert os.environ["DATABASE_PATH"] == str(moved)


def test_a_move_into_an_unusable_folder_is_refused_and_changes_nothing(serve, store, env, tmp_path):
    server = serve(store, env_path=env)

    status, message = failure(server, "POST", "/api/database/location", {"folder": str(tmp_path / "gone")})

    assert status == 400
    assert "isn't a folder" in message
    assert (tmp_path / "budget.db").exists()
    assert env.read_text(encoding="utf-8") == ENV
    assert call(server, "GET", "/api/database")[1]["path"] == str((tmp_path / "budget.db").resolve())


def test_a_move_without_a_folder_is_a_bad_request(serve, store, env):
    server = serve(store, env_path=env)

    assert failure(server, "POST", "/api/database/location", {})[0] == 400
