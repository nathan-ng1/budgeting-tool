"""Changing the Database's location when there is no `DATABASE_PATH` override:
the new location goes to the pointer file, `.env` is left alone (Issue #238,
ADR-0032). With an override, `.env` is rewritten - covered in test_database_move.py.
"""

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from dashboard.database_handle import DatabaseHandle
from dashboard.database_move import MoveFailed, apply_folder
from database.location import POINTER_FILE_NAME, SOURCE_OVERRIDE, SOURCE_POINTER, resolve_location, write_pointer
from database.store import connect


@pytest.fixture
def home(tmp_path: Path, monkeypatch):
    """A live Database in the default data folder, no override anywhere, an empty target folder."""
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    data = tmp_path / "user-data"
    data.mkdir()
    store = connect(data / "budget.db")
    store.write_settings({"currency": "GBP"})
    target = tmp_path / "Dropbox"
    target.mkdir()
    env = tmp_path / ".env"  # absent: a Retail install has none
    return type("Home", (), {"handle": DatabaseHandle(store), "data": data, "target": target, "env": env})


def located(home):
    return resolve_location(env_path=home.env, data_folder=home.data, environ=os.environ)


def test_a_move_writes_the_pointer_file_and_leaves_env_and_the_environment_alone(home):
    apply_folder(home.handle, str(home.target), home.env, data_folder=home.data)

    moved = home.target.resolve() / "budget.db"
    assert home.handle.path == moved
    assert home.handle.read_settings()["currency"] == "GBP"
    assert not (home.data / "budget.db").exists()
    assert located(home).path == moved
    assert located(home).source == SOURCE_POINTER
    assert not home.env.exists()
    assert "DATABASE_PATH" not in os.environ


def test_a_move_replaces_an_older_pointer(home, tmp_path):
    write_pointer(home.data, home.data / "budget.db")

    apply_folder(home.handle, str(home.target), home.env, data_folder=home.data)

    assert located(home).path == home.target.resolve() / "budget.db"


def test_switching_to_a_database_already_in_the_folder_writes_the_pointer_file(home):
    other = connect(home.target / "budget.db")
    other.write_settings({"currency": "EUR"})
    other.close()

    apply_folder(home.handle, str(home.target), home.env, data_folder=home.data)

    assert located(home).path == home.target.resolve() / "budget.db"
    assert home.handle.read_settings()["currency"] == "EUR"
    assert (home.data / "budget.db").exists()  # the old one is kept
    assert not home.env.exists()


def test_a_failed_pointer_write_during_a_move_leaves_everything_as_it_was(home):
    write_pointer(home.data, home.data / "budget.db")
    pointer_before = (home.data / POINTER_FILE_NAME).read_bytes()
    opened = []

    def tracking_open(path):
        opened.append(connect(path))
        return opened[-1]

    def cannot_write(folder, database_file):
        raise OSError("disk full")

    with pytest.raises(MoveFailed, match="disk full"):
        apply_folder(
            home.handle,
            str(home.target),
            home.env,
            data_folder=home.data,
            open_store=tracking_open,
            write_pointer_file=cannot_write,
        )

    assert (home.data / "budget.db").exists()
    assert (home.data / POINTER_FILE_NAME).read_bytes() == pointer_before
    assert list(home.target.iterdir()) == []  # the copy was cleaned up
    assert not home.env.exists()
    assert home.handle.path == (home.data / "budget.db").resolve()
    assert home.handle.read_settings()["currency"] == "GBP"
    with pytest.raises(sqlite3.ProgrammingError):
        opened[0].read_settings()  # closed


def test_a_failed_pointer_write_while_switching_leaves_everything_as_it_was(home):
    connect(home.target / "budget.db").close()

    def cannot_write(folder, database_file):
        raise OSError("disk full")

    with pytest.raises(MoveFailed, match="disk full"):
        apply_folder(home.handle, str(home.target), home.env, data_folder=home.data, write_pointer_file=cannot_write)

    assert home.handle.path == (home.data / "budget.db").resolve()
    assert not (home.data / POINTER_FILE_NAME).exists()
    assert (home.target / "budget.db").exists()  # the user's file is never removed


def test_a_dotenv_value_alone_counts_as_an_override_and_is_rewritten(home):
    home.env.write_text("DATABASE_PATH=somewhere.db\n", encoding="utf-8")

    try:
        apply_folder(home.handle, str(home.target), home.env, data_folder=home.data)
        moved = home.target.resolve() / "budget.db"
        assert home.env.read_text(encoding="utf-8") == f"DATABASE_PATH={moved}\n"
        assert not (home.data / POINTER_FILE_NAME).exists()
        assert located(home).source == SOURCE_OVERRIDE
    finally:
        os.environ.pop("DATABASE_PATH", None)


def call(server, method: str, path: str, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    with urlopen(Request(f"http://127.0.0.1:{server.server_port}{path}", data=body, method=method)) as response:
        return response.status, json.loads(response.read())


def test_confirming_over_http_without_an_override_writes_the_pointer_file(serve, home):
    server = serve(home.handle, env_path=home.env, data_folder=home.data)

    status, body = call(server, "POST", "/api/database/location", {"folder": str(home.target)})

    moved = home.target.resolve() / "budget.db"
    assert status == 200
    assert body["path"] == str(moved)
    assert call(server, "GET", "/api/settings")[1]["currency"] == "GBP"
    assert located(home).path == moved
    assert not home.env.exists()
    with closing(sqlite3.connect(moved)) as connection:
        assert connection.execute("SELECT 1 FROM sqlite_master WHERE name = 'transactions'").fetchone()
