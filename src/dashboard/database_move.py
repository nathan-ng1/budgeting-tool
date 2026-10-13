"""Choosing a new folder for the Database, and moving it there (Issue #198,
ADR-0030).

Two steps, so the confirmation UI can sit between them and later tickets can
add cases without reshaping the flow:

1. `inspect_folder` - what does the chosen folder hold? It reports an
   `outcome`: "move" (no Database there - the current one will be moved in),
   "current" (it is the folder the Database already lives in) or "existing"
   (a Database is already there - #199 switches to it).
2. `apply_folder` - act on that outcome. Only "move" is implemented here;
   the other outcomes are refused until their tickets land.

A failure at any step of a move leaves the live Database, its files and
`.env` exactly as they were; whatever was copied is cleaned up.
"""

import os
import shutil
import sqlite3
import tempfile
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from database.store import connect
from setup.env_file import write_env

OUTCOME_MOVE = "move"
OUTCOME_CURRENT = "current"
OUTCOME_EXISTING = "existing"


class FolderUnusable(ValueError):
    """The chosen folder can't be used; the message says why."""


class MoveFailed(Exception):
    """A step of the move failed; the Database and `.env` were left as they were."""


@dataclass(frozen=True)
class FolderReport:
    folder: Path
    outcome: str
    target: Path  # where the Database file is, or would be, in `folder`


def check_writable(folder: Path) -> None:
    """Raise FolderUnusable unless a file can be created in `folder`."""
    try:
        with tempfile.TemporaryFile(dir=folder):
            pass
    except OSError as cause:
        raise FolderUnusable(f"Can't write to {folder}: {cause.strerror or cause}") from cause


def inspect_folder(
    chosen: str,
    current_database: Path,
    *,
    ensure_writable: Callable[[Path], None] = check_writable,
) -> FolderReport:
    folder = Path(chosen)
    if not folder.is_dir():
        raise FolderUnusable(f"{chosen} isn't a folder that exists")
    folder = folder.resolve()
    target = folder / current_database.name

    if folder == current_database.resolve().parent:
        return FolderReport(folder, OUTCOME_CURRENT, target)

    ensure_writable(folder)
    outcome = OUTCOME_EXISTING if target.exists() else OUTCOME_MOVE
    return FolderReport(folder, outcome, target)


def report_payload(report: FolderReport) -> dict:
    return {
        "cancelled": False,
        "folder": str(report.folder),
        "outcome": report.outcome,
        "target": str(report.target),
    }


def pre_migration_files(database: Path) -> list[Path]:
    """The `*.pre-migration-*.db` copies beside `database` (see `python -m migration`)."""
    return sorted(database.parent.glob(f"{database.stem}.pre-migration-*{database.suffix}"))


def check_copy(copy: Path) -> None:
    """Raise MoveFailed unless `copy` is a readable, intact SQLite file."""
    try:
        with closing(sqlite3.connect(f"{copy.as_uri()}?mode=ro", uri=True)) as connection:
            verdict = connection.execute("PRAGMA integrity_check").fetchall()
    except sqlite3.Error as cause:
        raise MoveFailed(f"The copy of {copy.name} couldn't be checked: {cause}") from cause
    if verdict != [("ok",)]:
        raise MoveFailed(f"The copy of {copy.name} failed its integrity check")


def apply_folder(
    handle,
    chosen: str,
    env_path: Path,
    *,
    ensure_writable: Callable[[Path], None] = check_writable,
    verify_copy: Callable[[Path], None] = check_copy,
    open_store: Callable[[Path], object] = connect,
    write_location: Callable[[Path, dict[str, str]], None] = write_env,
) -> None:
    """Carry out the confirmed choice of `chosen` as the Database's folder."""
    report = inspect_folder(chosen, Path(handle.path), ensure_writable=ensure_writable)
    if report.outcome == OUTCOME_CURRENT:
        raise FolderUnusable("The Database is already in that folder")
    if report.outcome == OUTCOME_EXISTING:
        raise FolderUnusable("That folder already holds a Database")  # #199 replaces this
    _move(handle, report, env_path, verify_copy, open_store, write_location)


def _move(handle, report, env_path, verify_copy, open_store, write_location) -> None:
    old_database = Path(handle.path)
    sources = [old_database, *pre_migration_files(old_database)]
    # Never overwrite (or, on rollback, delete) a file that was already there.
    clashes = [source.name for source in sources if (report.folder / source.name).exists()]
    if clashes:
        raise FolderUnusable(f"That folder already holds {', '.join(clashes)}")
    copies: list[Path] = []
    new_store = None
    try:
        for source in sources:
            copy = report.folder / source.name
            copies.append(copy)
            shutil.copy2(source, copy)
        for copy in copies:
            verify_copy(copy)

        new_store = open_store(report.target)

        # `.env` is rewritten only now that the new connection opened, and the
        # live swap comes after it, so a failure up to here changes nothing.
        try:
            write_location(env_path, {"DATABASE_PATH": str(report.target)})
        except OSError as cause:
            raise MoveFailed(f"Couldn't update .env: {cause}") from cause
        os.environ["DATABASE_PATH"] = str(report.target)
    except BaseException as failure:
        if new_store is not None:
            new_store.close()
        _remove(copies)
        if isinstance(failure, (FolderUnusable, MoveFailed)):
            raise
        if isinstance(failure, Exception):
            raise MoveFailed(f"Couldn't move the Database: {failure}") from failure
        raise

    old_store = handle.swap(new_store)
    # Windows won't delete an open SQLite file.
    old_store.close()
    _remove(sources)


def _remove(files: list[Path]) -> None:
    for file in files:
        try:
            file.unlink(missing_ok=True)
        except OSError:
            # The move itself has succeeded (or is being rolled back); a file
            # that won't go is left for the user rather than failing the move.
            pass
