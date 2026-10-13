"""Moving the Database to another folder (Issue #198, ADR-0030).

Real Databases and a temporary `.env` in temporary folders; failing steps are
injected through `apply_folder`'s keyword arguments.
"""

import os
from pathlib import Path

import pytest

from dashboard import database_move
from dashboard.database_handle import DatabaseHandle
from dashboard.database_move import FolderUnusable, MoveFailed, apply_folder, inspect_folder
from database.store import connect

ENV = "# mine\nTRANSACTIONS_INBOX=C:\\In\nDATABASE_PATH= .data/budget.db\nBEEM_USERNAME=nathan\n"


@pytest.fixture
def home(tmp_path: Path, monkeypatch):
    """A live Database (with a pre-migration copy beside it), a `.env`, and an empty target folder."""
    monkeypatch.setenv("DATABASE_PATH", "original")
    source = tmp_path / "old"
    source.mkdir()
    store = connect(source / "budget.db")
    store.write_settings({"currency": "GBP"})
    connect(source / "budget.pre-migration-20260101-000000.db").close()
    env = tmp_path / ".env"
    env.write_text(ENV, encoding="utf-8")
    target = tmp_path / "new"
    target.mkdir()
    return type("Home", (), {"handle": DatabaseHandle(store), "source": source, "env": env, "target": target})


def untouched(home):
    assert (home.source / "budget.db").exists()
    assert (home.source / "budget.pre-migration-20260101-000000.db").exists()
    assert home.env.read_text(encoding="utf-8") == ENV
    assert os.environ["DATABASE_PATH"] == "original"
    assert home.handle.path == (home.source / "budget.db").resolve()
    assert home.handle.read_settings()["currency"] == "GBP"  # the live connection still works
    assert sorted(p.name for p in home.target.iterdir()) == []


def test_an_empty_folder_is_reported_as_a_move_target(home):
    report = inspect_folder(str(home.target), home.handle.path)

    assert report.outcome == "move"
    assert report.target == home.target.resolve() / "budget.db"


def test_the_folder_holding_the_current_database_is_reported_as_current(home):
    assert inspect_folder(str(home.source), home.handle.path).outcome == "current"


def test_a_folder_that_already_holds_a_database_is_reported_as_existing(home):
    (home.target / "budget.db").write_bytes(b"anything")

    assert inspect_folder(str(home.target), home.handle.path).outcome == "existing"


def test_a_folder_that_does_not_exist_is_refused(home, tmp_path):
    with pytest.raises(FolderUnusable, match="isn't a folder"):
        inspect_folder(str(tmp_path / "nope"), home.handle.path)


def test_an_unwritable_folder_is_refused(home):
    def cannot_write(folder):
        raise FolderUnusable("Can't write")

    with pytest.raises(FolderUnusable):
        inspect_folder(str(home.target), home.handle.path, ensure_writable=cannot_write)


def test_the_real_writability_check_accepts_a_normal_folder_and_rejects_a_missing_one(tmp_path):
    database_move.check_writable(tmp_path)
    with pytest.raises(FolderUnusable):
        database_move.check_writable(tmp_path / "missing")


def test_a_move_serves_the_same_data_from_the_new_folder_and_removes_the_old_files(home):
    old_store = home.handle.store

    apply_folder(home.handle, str(home.target), home.env)

    new_database = home.target.resolve() / "budget.db"
    assert home.handle.path == new_database
    assert home.handle.read_settings()["currency"] == "GBP"
    assert (home.target / "budget.pre-migration-20260101-000000.db").exists()
    assert not (home.source / "budget.db").exists()
    assert not (home.source / "budget.pre-migration-20260101-000000.db").exists()
    with pytest.raises(Exception):
        old_store.read_settings()  # the old connection was closed


def test_a_move_rewrites_only_database_path_in_env_with_an_absolute_path(home):
    apply_folder(home.handle, str(home.target), home.env)

    assert home.env.read_text(encoding="utf-8") == ENV.replace(
        "DATABASE_PATH= .data/budget.db", f"DATABASE_PATH={home.target.resolve() / 'budget.db'}"
    )
    assert os.environ["DATABASE_PATH"] == str(home.target.resolve() / "budget.db")


def test_choosing_the_current_or_an_existing_folder_is_not_a_move(home):
    with pytest.raises(FolderUnusable):
        apply_folder(home.handle, str(home.source), home.env)

    (home.target / "budget.db").write_bytes(b"x")
    with pytest.raises(FolderUnusable):
        apply_folder(home.handle, str(home.target), home.env)
    assert (home.source / "budget.db").exists()


def test_a_folder_already_holding_a_pre_migration_file_of_the_same_name_is_refused_untouched(home):
    clash = home.target / "budget.pre-migration-20260101-000000.db"
    clash.write_bytes(b"precious")

    with pytest.raises(FolderUnusable):
        apply_folder(home.handle, str(home.target), home.env)

    assert clash.read_bytes() == b"precious"
    assert (home.source / "budget.db").exists()


def test_an_unwritable_folder_leaves_everything_as_it_was(home):
    def cannot_write(folder):
        raise FolderUnusable("Can't write")

    with pytest.raises(FolderUnusable):
        apply_folder(home.handle, str(home.target), home.env, ensure_writable=cannot_write)

    untouched(home)


def test_a_failed_copy_leaves_everything_as_it_was(home, monkeypatch):
    real_copy = database_move.shutil.copy2
    calls = []

    def copy_then_die(source, destination):
        calls.append(source)
        if len(calls) == 2:
            raise OSError("disk full")
        return real_copy(source, destination)

    monkeypatch.setattr(database_move.shutil, "copy2", copy_then_die)

    with pytest.raises(MoveFailed, match="disk full"):
        apply_folder(home.handle, str(home.target), home.env)

    untouched(home)


def test_a_failed_integrity_check_leaves_everything_as_it_was(home):
    def corrupt(copy):
        raise MoveFailed("failed its integrity check")

    with pytest.raises(MoveFailed, match="integrity"):
        apply_folder(home.handle, str(home.target), home.env, verify_copy=corrupt)

    untouched(home)


def test_the_real_integrity_check_rejects_a_damaged_copy(tmp_path):
    damaged = tmp_path / "damaged.db"
    damaged.write_bytes(b"this is not a database" * 100)

    with pytest.raises(MoveFailed):
        database_move.check_copy(damaged)


def test_the_real_integrity_check_accepts_an_intact_database(home):
    database_move.check_copy(home.source / "budget.db")


def test_a_failed_connection_leaves_everything_as_it_was(home):
    def cannot_open(path):
        raise OSError("cannot open")

    with pytest.raises(MoveFailed, match="cannot open"):
        apply_folder(home.handle, str(home.target), home.env, open_store=cannot_open)

    untouched(home)


def test_a_failed_env_write_leaves_everything_as_it_was_and_closes_the_new_connection(home):
    opened = []

    def tracking_open(path):
        opened.append(connect(path))
        return opened[-1]

    def cannot_write_env(env_path, values):
        raise OSError("env is read-only")

    with pytest.raises(MoveFailed, match="\\.env"):
        apply_folder(
            home.handle, str(home.target), home.env, open_store=tracking_open, write_location=cannot_write_env
        )

    untouched(home)
    with pytest.raises(Exception):
        opened[0].read_settings()


def test_nothing_old_is_deleted_until_the_switch_has_happened(home):
    seen = {}

    def write_and_look(env_path, values):
        seen["old_still_there"] = (home.source / "budget.db").exists()
        seen["handle_still_old"] = home.handle.path == (home.source / "budget.db").resolve()
        database_move.write_env(env_path, values)

    apply_folder(home.handle, str(home.target), home.env, write_location=write_and_look)

    assert seen == {"old_still_there": True, "handle_still_old": True}
    assert not (home.source / "budget.db").exists()
