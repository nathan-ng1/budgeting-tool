"""Changing the Database's location over real HTTP, with a stand-in folder
picker and a temporary `.env` (Issue #198, ADR-0030)."""

import json
import os
import sqlite3
import threading
from contextlib import closing
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from dashboard.folder_picker import FolderPickerError
from database.store import connect

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


# --- switching to the Database already in the chosen folder (Issue #199) ---


@pytest.fixture
def restored(tmp_path: Path, new_folder):
    """A Backup-like file (sqlite3's backup API) of another Database, placed in `new_folder`."""
    other = connect(tmp_path / "elsewhere.db")
    other.write_settings({"currency": "EUR"})
    other.close()
    with closing(sqlite3.connect(tmp_path / "elsewhere.db")) as source:
        with closing(sqlite3.connect(new_folder / "budget.db")) as copy:
            source.backup(copy)
    return new_folder / "budget.db"


def test_choosing_a_folder_holding_a_database_reports_that_it_will_be_switched_to(serve, store, env, new_folder, restored):
    server = serve(store, env_path=env, pick_folder=lambda: str(new_folder))

    status, body = call(server, "POST", "/api/database/choose-folder")

    assert status == 200
    assert body["outcome"] == "existing"
    assert body["target"] == str(restored.resolve())
    assert env.read_text(encoding="utf-8") == ENV


def test_confirming_switches_live_to_the_database_in_the_folder_and_leaves_the_current_one(
    serve, store, env, new_folder, restored, tmp_path
):
    store.write_settings({"currency": "GBP"})
    server = serve(store, env_path=env)

    status, body = call(server, "POST", "/api/database/location", {"folder": str(new_folder)})

    assert status == 200
    assert body["path"] == str(restored.resolve())
    assert call(server, "GET", "/api/database")[1]["path"] == str(restored.resolve())
    assert call(server, "GET", "/api/settings")[1]["currency"] == "EUR"
    assert (tmp_path / "budget.db").exists()
    with closing(sqlite3.connect(tmp_path / "budget.db")) as old:
        assert old.execute("SELECT value FROM settings WHERE key = 'currency'").fetchone() == ("GBP",)
    assert env.read_text(encoding="utf-8") == f"# mine\nDATABASE_PATH={restored.resolve()}\nBEEM_USERNAME=nathan\n"
    assert os.environ["DATABASE_PATH"] == str(restored.resolve())


@pytest.mark.parametrize("content", [b"definitely not sqlite " * 50, b""])
def test_a_file_that_is_not_one_of_ours_is_refused_and_changes_nothing(serve, store, env, new_folder, tmp_path, content):
    (new_folder / "budget.db").write_bytes(content)
    server = serve(store, env_path=env, pick_folder=lambda: str(new_folder))

    chosen = failure(server, "POST", "/api/database/choose-folder")
    applied = failure(server, "POST", "/api/database/location", {"folder": str(new_folder)})

    for status, message in (chosen, applied):
        assert status == 400
        assert "isn't a Budgeting Tool Database" in message
    assert (new_folder / "budget.db").read_bytes() == content
    assert env.read_text(encoding="utf-8") == ENV
    assert call(server, "GET", "/api/database")[1]["path"] == str((tmp_path / "budget.db").resolve())


def test_a_sqlite_file_without_our_tables_is_refused_untouched(serve, store, env, new_folder, tmp_path):
    with closing(sqlite3.connect(new_folder / "budget.db")) as other:
        other.execute("CREATE TABLE notes (body TEXT)")
        other.commit()
    before = (new_folder / "budget.db").read_bytes()
    server = serve(store, env_path=env)

    status, message = failure(server, "POST", "/api/database/location", {"folder": str(new_folder)})

    assert status == 400
    assert "isn't a Budgeting Tool Database" in message
    assert (new_folder / "budget.db").read_bytes() == before  # no tables created or migrations marked
    assert env.read_text(encoding="utf-8") == ENV


# --- restoring a downloaded Backup under its default name (Issue #199) ---


def download_backup(server, folder: Path) -> Path:
    """GET the Backup the way the browser would and save it under its default name."""
    with urlopen(f"http://127.0.0.1:{server.server_port}/api/database/backup") as response:
        disposition = response.headers["Content-Disposition"]
        body = response.read()
    name = disposition.split('filename="')[1].rstrip('"')
    (folder / name).write_bytes(body)
    return folder / name


def test_a_backup_saved_under_its_default_name_can_be_switched_to(serve, store, env, new_folder, tmp_path):
    store.write_settings({"currency": "EUR"})
    server = serve(store, env_path=env, pick_folder=lambda: str(new_folder))
    backup = download_backup(server, new_folder)
    assert backup.name != "budget.db"
    store.write_settings({"currency": "GBP"})

    chosen = call(server, "POST", "/api/database/choose-folder")[1]
    status, body = call(server, "POST", "/api/database/location", {"folder": str(new_folder)})

    assert chosen["outcome"] == "existing"
    assert chosen["target"] == str(backup.resolve())
    assert status == 200
    assert body["path"] == str(backup.resolve())
    assert call(server, "GET", "/api/settings")[1]["currency"] == "EUR"
    assert (tmp_path / "budget.db").exists()  # the live Database stays where it was
    assert not (new_folder / "budget.db").exists()
    assert env.read_text(encoding="utf-8") == f"# mine\nDATABASE_PATH={backup.resolve()}\nBEEM_USERNAME=nathan\n"


def test_two_backups_in_one_folder_are_refused_asking_for_just_one(serve, store, env, new_folder, tmp_path):
    server = serve(store, env_path=env, pick_folder=lambda: str(new_folder))
    first = download_backup(server, new_folder)
    second = new_folder / "budget-backup-20200101-000000.db"
    second.write_bytes(first.read_bytes())

    for request in (
        lambda: failure(server, "POST", "/api/database/choose-folder"),
        lambda: failure(server, "POST", "/api/database/location", {"folder": str(new_folder)}),
    ):
        status, message = request()
        assert status == 400
        assert "just one" in message
    assert (tmp_path / "budget.db").exists()
    assert env.read_text(encoding="utf-8") == ENV
    assert call(server, "GET", "/api/database")[1]["path"] == str((tmp_path / "budget.db").resolve())


def test_a_file_named_like_the_database_wins_over_a_backup_beside_it(serve, store, env, new_folder, restored):
    server = serve(store, env_path=env, pick_folder=lambda: str(new_folder))
    download_backup(server, new_folder)

    assert call(server, "POST", "/api/database/choose-folder")[1]["target"] == str(restored.resolve())


def test_a_move_tells_the_user_which_old_files_could_not_be_removed(serve, store, env, new_folder, tmp_path, monkeypatch):
    real_unlink = Path.unlink

    def unlink(self, *args, **kwargs):
        if self == (tmp_path / "budget.db").resolve():
            raise PermissionError("in use")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", unlink)
    server = serve(store, env_path=env)

    status, body = call(server, "POST", "/api/database/location", {"folder": str(new_folder)})

    assert status == 200
    assert body["path"] == str(new_folder.resolve() / "budget.db")
    assert body["left_behind"] == [str((tmp_path / "budget.db").resolve())]
    assert "left_behind" not in call(server, "GET", "/api/database")[1]


def test_an_open_folder_dialog_does_not_freeze_the_rest_of_the_dashboard(serve, store, env, new_folder):
    dialog_open = threading.Event()
    close_dialog = threading.Event()

    def slow_picker():
        dialog_open.set()
        assert close_dialog.wait(timeout=10)
        return str(new_folder)

    server = serve(store, env_path=env, pick_folder=slow_picker)
    answer = []
    chooser = threading.Thread(target=lambda: answer.append(call(server, "POST", "/api/database/choose-folder")))
    chooser.start()
    try:
        assert dialog_open.wait(timeout=10)
        assert call(server, "GET", "/api/settings")[0] == 200  # not queued behind the dialog
    finally:
        close_dialog.set()
        chooser.join(timeout=10)

    assert answer[0][1]["outcome"] == "move"
