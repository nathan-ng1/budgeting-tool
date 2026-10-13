"""Deleting all data and resetting the Dashboard (Issue #201, ADR-0030).

The Database file and every `*.pre-migration-*.db` beside it are deleted and a
brand-new empty Database (default Categories seeded) is opened at the same
path through the swappable handle, which is never left holding a closed
connection. `.env` is untouched, and so is everything
else that is not the Database: the Processed archive and the Transactions
Inbox live elsewhere and are never looked at.

The typed `DELETE` is checked here, on the server, as well as in the dialog,
so a stray or scripted call does nothing.
"""

import os
from collections.abc import Callable
from pathlib import Path

from dashboard.database_move import pre_migration_files
from database.store import connect

CONFIRMATION = "DELETE"


class ConfirmationMissing(ValueError):
    """The request didn't carry the typed confirmation; nothing was deleted."""


class ResetFailed(Exception):
    """The reset didn't complete; the message says what state things are in."""


class DatabaseUnavailable(Exception):
    """Raised by the placeholder that stands in for the Database when a reset
    deleted it but could not open the new one."""


class _Unavailable:
    """Stands in for the open Database after a reset that deleted the old one
    and could not open the new one, so the handle never holds a closed
    connection. Every use reports why instead of failing obscurely."""

    def __init__(self, path: Path, reason: str):
        self.path = path
        self._reason = reason

    def close(self) -> None:
        pass

    def __getattr__(self, name):
        raise DatabaseUnavailable(self._reason)


def summary_payload(handle) -> dict:
    """What a reset would delete, live: the Database's path, the row counts
    from `LocalStore.count_data`, and how many pre-migration copies go too."""
    path = Path(handle.path)
    return {"path": str(path), **handle.count_data(), "pre_migration_files": len(pre_migration_files(path))}


def check_confirmation(payload) -> None:
    if not isinstance(payload, dict) or payload.get("confirmation") != CONFIRMATION:
        raise ConfirmationMissing(f"Type {CONFIRMATION} to confirm deleting all data")


def reset(handle, *, open_store: Callable[[Path], object] = connect) -> Path:
    """Delete the Database and its pre-migration copies, then serve a fresh
    empty Database at the same path. Returns that path.

    The fresh Database is built first, beside the old one, so a disk or
    open problem is found while nothing has been deleted. Then the old
    connection is released (Windows won't delete an open SQLite file) and the
    pre-migration copies go before the Database file itself, so a file that
    won't delete leaves the data in place: the Database is reopened and the
    reset reported as failed (some copies may already be gone).
    """
    path = Path(handle.path)
    copies = pre_migration_files(path)
    fresh = path.with_name(f"{path.stem}.fresh{path.suffix}.tmp")

    try:
        fresh.unlink(missing_ok=True)
        open_store(fresh).close()
    except Exception as cause:
        fresh.unlink(missing_ok=True)
        raise ResetFailed(f"Couldn't prepare a new Database, so nothing was deleted: {cause}") from cause

    handle.store.close()
    try:
        for file in [*copies, path]:
            file.unlink(missing_ok=True)
    except OSError as cause:
        fresh.unlink(missing_ok=True)
        _reopen(handle, path, open_store, f"Couldn't delete {file.name}: {cause.strerror or cause}")
        raise ResetFailed(
            f"Couldn't delete {file.name}: {cause.strerror or cause}. "
            f"Your Database was kept{'' if file == path else ' (some pre-migration copies may already be gone)'}."
        ) from cause

    try:
        os.replace(fresh, path)
        handle.swap(open_store(path))
    except Exception as cause:
        message = f"Your data was deleted but the new Database couldn't be opened: {cause}. Restart the Dashboard."
        handle.swap(_Unavailable(path, message))
        raise ResetFailed(message) from cause
    return path


def _reopen(handle, path: Path, open_store, reason: str) -> None:
    """Put a working connection back after the old one was closed."""
    try:
        handle.swap(open_store(path))
    except Exception as cause:
        message = f"{reason}. The Database couldn't be reopened either: {cause}. Restart the Dashboard."
        handle.swap(_Unavailable(path, message))
        raise ResetFailed(message) from cause
