"""Failures during a reset (Issue #201, ADR-0030): whatever goes wrong, the
handle is never left holding a closed connection and the outcome is reported
accurately. Real Databases in temporary folders; failures injected through
`reset`'s `open_store` and a patched `Path.unlink`."""

import sqlite3
from pathlib import Path

import pytest

from dashboard.database_handle import DatabaseHandle
from dashboard.database_reset import DatabaseUnavailable, ResetFailed, reset
from database.store import connect

COPIES = ("budget.pre-migration-20260101-000000.db", "budget.pre-migration-20260102-000000.db")


@pytest.fixture
def home(tmp_path: Path):
    store = connect(tmp_path / "budget.db")
    store.write_settings({"currency": "GBP"})
    for name in COPIES:
        (tmp_path / name).write_bytes(b"old")
    return tmp_path, DatabaseHandle(store)


def failing_unlink(monkeypatch, name: str):
    real_unlink = Path.unlink

    def unlink(self, *args, **kwargs):
        if self.name == name:
            raise PermissionError(13, "The file is in use")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", unlink)


def test_a_reset_replaces_the_database_with_a_fresh_one_and_leaves_no_scratch_file(home):
    folder, handle = home

    reset(handle)

    assert handle.read_settings() == {}
    assert sorted(p.name for p in folder.iterdir()) == ["budget.db"]


def test_a_copy_that_will_not_delete_keeps_the_data_and_the_handle_working(home, monkeypatch):
    folder, handle = home
    failing_unlink(monkeypatch, COPIES[1])

    with pytest.raises(ResetFailed, match="Your Database was kept"):
        reset(handle)

    assert handle.read_settings()["currency"] == "GBP"  # a live connection to the surviving data
    assert (folder / "budget.db").exists()
    assert not (folder / "budget.fresh.db.tmp").exists()


def test_a_database_file_that_will_not_delete_keeps_the_data_and_the_handle_working(home, monkeypatch):
    folder, handle = home
    failing_unlink(monkeypatch, "budget.db")

    with pytest.raises(ResetFailed, match="Your Database was kept"):
        reset(handle)

    assert handle.read_settings()["currency"] == "GBP"
    assert not (folder / "budget.fresh.db.tmp").exists()


def test_an_open_that_fails_before_anything_is_deleted_changes_nothing(home):
    folder, handle = home
    original = handle.store

    def cannot_open(path):
        raise sqlite3.OperationalError("disk full")

    with pytest.raises(ResetFailed, match="nothing was deleted"):
        reset(handle, open_store=cannot_open)

    assert handle.store is original
    assert handle.read_settings()["currency"] == "GBP"
    assert all((folder / name).exists() for name in COPIES)


def test_an_open_that_fails_after_the_delete_leaves_a_handle_that_explains_itself(home):
    folder, handle = home

    def fails_on_the_real_path(path):
        if path.name == "budget.db":
            raise sqlite3.OperationalError("unable to open")
        return connect(path)

    with pytest.raises(ResetFailed, match="Restart the Dashboard"):
        reset(handle, open_store=fails_on_the_real_path)

    with pytest.raises(DatabaseUnavailable, match="unable to open"):  # not an obscure closed-connection error
        handle.read_settings()
    assert handle.path == folder / "budget.db"


def test_a_reopen_that_fails_after_a_delete_failure_leaves_a_handle_that_explains_itself(home, monkeypatch):
    folder, handle = home
    failing_unlink(monkeypatch, "budget.db")

    def fails_on_the_real_path(path):
        if path.name == "budget.db":
            raise sqlite3.OperationalError("unable to open")
        return connect(path)

    with pytest.raises(ResetFailed, match="couldn't be reopened"):
        reset(handle, open_store=fails_on_the_real_path)

    with pytest.raises(DatabaseUnavailable):
        handle.read_settings()
