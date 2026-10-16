"""Every entry point finds the Database through the one resolver (Issue #238,
ADR-0032): the store (and so the pipeline scripts and the Budget Suggestion
flow), the migration runner behind the update scripts, and the Dashboard."""

from pathlib import Path

import pytest

from dashboard import __main__ as dashboard_main
from database import location
from database.location import write_pointer
from database.store import connect, open_connection
from migration import __main__ as migration_main


@pytest.fixture
def data_folder() -> Path:
    """The (test-isolated) default per-user data folder."""
    return location.default_data_folder()


@pytest.fixture
def pointed(tmp_path: Path, data_folder: Path) -> Path:
    """A Database elsewhere that the pointer file names."""
    elsewhere = tmp_path / "Dropbox"
    elsewhere.mkdir()
    path = elsewhere / "budget.db"
    connect(path).close()
    write_pointer(data_folder, path)
    return path


def test_a_fresh_install_gets_a_database_in_the_default_data_folder(data_folder):
    store = connect()
    store.close()

    assert store.path == (data_folder / "budget.db").resolve()
    assert store.path.exists()


def test_the_store_opens_the_database_the_pointer_names(pointed):
    store = connect()
    store.close()

    assert store.path == pointed.resolve()


def test_an_override_still_wins_over_the_pointer_for_the_store(pointed, tmp_path, monkeypatch):
    mine = tmp_path / "mine.db"
    monkeypatch.setenv("DATABASE_PATH", str(mine))

    store = connect()
    store.close()

    assert store.path == mine.resolve()


def test_a_dotenv_override_is_unchanged_for_a_collaborator_install(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("TRANSACTIONS_INBOX=C:\\In\nDATABASE_PATH= " + str(tmp_path / "kept.db") + "\n", encoding="utf-8")
    monkeypatch.setattr(location, "ENV_PATH", env)

    connection = open_connection()
    connection.close()

    assert (tmp_path / "kept.db").exists()


def test_the_migration_runner_follows_the_pointer(pointed, data_folder, capsys):
    assert migration_main.main() == 0

    assert "up to date" in capsys.readouterr().out
    assert not (data_folder / "budget.db").exists()  # no second, empty Database was started


def test_the_dashboard_serves_the_database_the_pointer_names(pointed, monkeypatch):
    monkeypatch.setattr(dashboard_main, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setenv("DASHBOARD_PORT", "0")
    seen = []

    class StubServer:
        server_port = 0

        def serve_forever(self):
            pass

        def server_close(self):
            pass

    monkeypatch.setattr(dashboard_main, "build_server", lambda store, port: seen.append(store.path) or StubServer())

    dashboard_main.main()

    assert seen == [pointed.resolve()]
