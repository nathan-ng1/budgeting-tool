"""The Dashboard refuses to start while migrations are pending (Goals spec
section 3, ADR-0019): it never runs them itself, since updating is a manual
step."""

import sqlite3
import threading
from pathlib import Path

import pytest

from dashboard import __main__ as dashboard_main
from database.store import connect

PRE_GOALS_SCHEMA = """
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, name TEXT NOT NULL UNIQUE,
    emoji TEXT, locked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, amount REAL NOT NULL,
    type TEXT NOT NULL, category_id INTEGER NOT NULL REFERENCES categories(id), notes TEXT NOT NULL
);
INSERT INTO categories (type, name) VALUES ('Savings', 'Savings');
"""


def old_install(tmp_path: Path) -> Path:
    path = tmp_path / "budget.db"
    connection = sqlite3.connect(path)
    connection.executescript(PRE_GOALS_SCHEMA)
    connection.commit()
    connection.close()
    return path


def test_main_refuses_to_start_on_an_install_with_pending_migrations(tmp_path: Path, monkeypatch):
    path = old_install(tmp_path)
    monkeypatch.setenv("DATABASE_PATH", str(path))
    monkeypatch.setattr(dashboard_main, "build_server", pytest.fail)

    with pytest.raises(SystemExit) as refused:
        dashboard_main.main()

    message = str(refused.value)
    assert "update" in message.lower()
    assert "add_goals" in message


def test_refusing_does_not_run_the_migrations(tmp_path: Path, monkeypatch):
    path = old_install(tmp_path)
    monkeypatch.setenv("DATABASE_PATH", str(path))

    with pytest.raises(SystemExit):
        dashboard_main.main()

    check = sqlite3.connect(path)
    assert "goal_id" not in [row[1] for row in check.execute("PRAGMA table_info(transactions)")]
    assert check.execute("SELECT COUNT(*) FROM categories WHERE name = 'Goals'").fetchone() == (0,)
    check.close()


def test_main_starts_serving_on_a_fully_migrated_database(tmp_path: Path, monkeypatch):
    path = tmp_path / "budget.db"
    connect(path).close()
    monkeypatch.setenv("DATABASE_PATH", str(path))
    monkeypatch.setenv("DASHBOARD_PORT", "0")
    served = threading.Event()

    class StubServer:
        server_port = 0

        def serve_forever(self):
            served.set()

        def server_close(self):
            pass

    monkeypatch.setattr(dashboard_main, "build_server", lambda store, port: StubServer())

    dashboard_main.main()

    assert served.is_set()
    check = connect(path)
    assert check.pending_migration_names() == []
    check.close()
