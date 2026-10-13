"""Switching to an older or newer Database over real HTTP (Issue #200, ADR-0030,
ADR-0025): an older one is migrated (after a pre-migration copy) and then used;
one made by a newer Dashboard is refused without being touched. Fixture
Databases are built by hand at each state, as the migration tests do."""

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from dashboard import database_move
from database.store import open_connection
from migration.registry import MIGRATIONS
from migration.runner import Migration

ENV = "# mine\nDATABASE_PATH= .data/budget.db\nBEEM_USERNAME=nathan\n"

PRE_90_SCHEMA = """
CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
    amount REAL NOT NULL, type TEXT NOT NULL, category TEXT NOT NULL, notes TEXT NOT NULL);
CREATE TABLE recurring_rules (id INTEGER PRIMARY KEY AUTOINCREMENT, amount REAL NOT NULL,
    type TEXT NOT NULL, category TEXT NOT NULL, notes TEXT NOT NULL, frequency TEXT NOT NULL,
    interval INTEGER NOT NULL, day TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT);
CREATE TABLE category_budgets (category TEXT NOT NULL, year INTEGER NOT NULL,
    month INTEGER NOT NULL, amount NUMERIC NOT NULL, PRIMARY KEY (category, year, month));
INSERT INTO transactions (date, amount, type, category, notes)
    VALUES ('2026-08-05', 42.5, 'Expense', 'Groceries', 'Woolworths');
"""


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
def folder(tmp_path: Path):
    path = tmp_path / "new"
    path.mkdir()
    return path


def no_tracking_database(folder: Path) -> Path:
    """An install from before Issue #90 that has never recorded a migration."""
    with closing(sqlite3.connect(folder / "budget.db")) as old:
        old.executescript(PRE_90_SCHEMA)
        old.commit()
    return folder / "budget.db"


def behind_database(folder: Path) -> Path:
    """A Database that tracks migrations but is missing the latest one."""
    connection = open_connection(folder / "budget.db")
    connection.execute("INSERT INTO categories (type, name, locked) VALUES ('Expense', 'Marker', 0)")
    connection.execute("DELETE FROM schema_migrations WHERE name = 'add_bills_and_subscriptions'")
    connection.execute("DELETE FROM categories WHERE type = 'Bills & Subscriptions'")
    connection.commit()
    connection.close()
    return folder / "budget.db"


def newer_database(folder: Path) -> Path:
    connection = open_connection(folder / "budget.db")
    connection.execute("INSERT INTO schema_migrations (name, applied_at) VALUES ('from_the_future', 'later')")
    connection.commit()
    connection.close()
    return folder / "budget.db"


def contents(path: Path) -> list[str]:
    with closing(sqlite3.connect(path)) as connection:
        return list(connection.iterdump())


def copies(folder: Path) -> list[Path]:
    return sorted(folder.glob("budget.pre-migration-*.db"))


def test_choosing_a_folder_with_an_older_database_reports_that_it_will_be_migrated(serve, store, env, folder):
    target = no_tracking_database(folder)
    before = target.read_bytes()
    server = serve(store, env_path=env, pick_folder=lambda: str(folder))

    status, body = call(server, "POST", "/api/database/choose-folder")

    assert status == 200
    assert body["outcome"] == "migrate"
    assert body["target"] == str(target.resolve())
    assert target.read_bytes() == before  # choosing changes nothing
    assert copies(folder) == []


def test_a_database_with_no_migration_tracking_is_copied_migrated_and_then_used_with_its_data_intact(
    serve, store, env, folder, tmp_path
):
    target = no_tracking_database(folder)
    server = serve(store, env_path=env)

    status, body = call(server, "POST", "/api/database/location", {"folder": str(folder)})

    assert status == 200
    assert body["path"] == str(target.resolve())
    assert call(server, "GET", "/api/database")[1]["path"] == str(target.resolve())
    assert env.read_text(encoding="utf-8") == f"# mine\nDATABASE_PATH={target.resolve()}\nBEEM_USERNAME=nathan\n"
    assert os.environ["DATABASE_PATH"] == str(target.resolve())
    with closing(sqlite3.connect(target)) as migrated:
        names = {name for (name,) in migrated.execute("SELECT name FROM schema_migrations")}
        assert names == {m.name for m in MIGRATIONS}
        assert migrated.execute(
            "SELECT t.amount, c.name, t.notes FROM transactions t JOIN categories c ON c.id = t.category_id"
        ).fetchall() == [(42.5, "Groceries", "Woolworths")]
    [copy] = copies(folder)
    with closing(sqlite3.connect(copy)) as before:  # the Database exactly as it was
        assert before.execute("SELECT category FROM transactions").fetchall() == [("Groceries",)]
        assert before.execute("SELECT 1 FROM sqlite_master WHERE name = 'schema_migrations'").fetchone() is None


def test_a_database_missing_only_the_latest_migration_is_migrated_and_used(serve, store, env, folder):
    target = behind_database(folder)
    server = serve(store, env_path=env)

    status, _body = call(server, "POST", "/api/database/location", {"folder": str(folder)})

    assert status == 200
    with closing(sqlite3.connect(target)) as migrated:
        assert migrated.execute("SELECT COUNT(*) FROM categories WHERE type = 'Bills & Subscriptions'").fetchone()[0] > 0
        assert migrated.execute("SELECT 1 FROM categories WHERE name = 'Marker'").fetchone() is not None
    [copy] = copies(folder)
    with closing(sqlite3.connect(copy)) as before:
        assert before.execute("SELECT COUNT(*) FROM categories WHERE type = 'Bills & Subscriptions'").fetchone()[0] == 0


def test_a_failing_migration_reports_why_restores_the_file_and_does_not_switch(
    serve, store, env, folder, tmp_path, monkeypatch
):
    target = no_tracking_database(folder)
    before = contents(target)

    def explode(connection):
        connection.execute("CREATE TABLE half_done (x)")
        connection.commit()
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(database_move, "MIGRATIONS", [*MIGRATIONS, Migration(name="explodes", migrate=explode)])
    server = serve(store, env_path=env)

    status, message = failure(server, "POST", "/api/database/location", {"folder": str(folder)})

    assert status in (400, 500)
    assert "explodes" in message
    assert "disk on fire" in message
    assert contents(target) == before  # restored: no half_done table, nothing marked applied
    assert copies(folder) == []  # nothing stale left beside it
    assert env.read_text(encoding="utf-8") == ENV
    assert os.environ["DATABASE_PATH"] == "original"
    assert call(server, "GET", "/api/database")[1]["path"] == str((tmp_path / "budget.db").resolve())


def test_a_database_recording_an_unknown_migration_is_refused_untouched(serve, store, env, folder, tmp_path):
    target = newer_database(folder)
    before = target.read_bytes()
    server = serve(store, env_path=env, pick_folder=lambda: str(folder))

    chosen = failure(server, "POST", "/api/database/choose-folder")
    applied = failure(server, "POST", "/api/database/location", {"folder": str(folder)})

    for status, message in (chosen, applied):
        assert status == 400
        assert "update the tool first" in message.lower()
    assert target.read_bytes() == before
    assert copies(folder) == []
    assert env.read_text(encoding="utf-8") == ENV
    assert call(server, "GET", "/api/database")[1]["path"] == str((tmp_path / "budget.db").resolve())
