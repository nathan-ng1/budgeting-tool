"""Deleting all data and resetting the Dashboard (Issue #201, ADR-0030).

The Database file and every `*.pre-migration-*.db` beside it are deleted and a
brand-new empty Database (default Categories seeded) is opened at the same
path through the swappable handle. `.env` is untouched, and so is everything
else that is not the Database: the Processed archive and the Transactions
Inbox live elsewhere and are never looked at.

The typed `DELETE` is checked here, on the server, as well as in the dialog,
so a stray or scripted call does nothing.
"""

from collections.abc import Callable
from pathlib import Path

from dashboard.database_move import pre_migration_files
from database.store import connect

CONFIRMATION = "DELETE"


class ConfirmationMissing(ValueError):
    """The request didn't carry the typed confirmation; nothing was deleted."""


class ResetFailed(Exception):
    """The files couldn't be deleted; the Database was reopened as it was."""


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
    empty Database at the same path. Returns that path."""
    path = Path(handle.path)
    doomed = [path, *pre_migration_files(path)]

    # Windows won't delete an open SQLite file, so release it first.
    handle.store.close()
    try:
        for file in doomed:
            file.unlink(missing_ok=True)
    except OSError as cause:
        # Put back a working connection to whatever survived, so the Dashboard
        # keeps serving rather than holding a closed one.
        handle.swap(open_store(path))
        raise ResetFailed(f"Couldn't delete {file.name}: {cause.strerror or cause}") from cause

    handle.swap(open_store(path))
    return path
