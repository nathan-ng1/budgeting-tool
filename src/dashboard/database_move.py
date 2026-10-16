"""Choosing a new folder for the Database, and moving it there (Issue #198,
ADR-0030).

Two steps, so the confirmation UI can sit between them and later tickets can
add cases without reshaping the flow:

1. `inspect_folder` - what does the chosen folder hold? It reports an
   `outcome`:
   - "move": no Database there; the current one will be moved in.
   - "current": it is the folder the Database already lives in.
   - "existing": a Database is already there; the Dashboard switches to it
     (Issue #199). That is the file named like the current Database or, failing
     that, a single downloaded Backup saved under its default name - so a
     Backup can be restored without renaming it. Several Backups and no
     Database is refused: the user is asked to leave just one.
   - "migrate": as "existing", but from an older version; it is copied to a
     `.pre-migration-` file, migrated, then switched to (Issue #200).
   A Database from a newer version is refused with "update the tool first".
2. `apply_folder` - act on that outcome: "move" copies the Database in,
   "existing" and "migrate" start using the one already there (keeping its
   file name) and leave the current one where it is.

A foreign file is judged by `check_foreign_database` on a plain, read-only
sqlite3 connection - never by `open_connection`, which would create tables,
seed Categories and mark migrations in a file that isn't ours to change.

Where the new location is recorded follows `database.location`: `.env` when a
`DATABASE_PATH` override exists (it would win over anything else), otherwise the
pointer file in the per-user data folder (Issue #238, ADR-0032).

A failure at any step leaves the live Database, its files, `.env` and the
pointer file exactly as they were; whatever a move copied is cleaned up, and a
Database that was already in the folder is never removed.
"""

import os
import re
import shutil
import sqlite3
import tempfile
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from database.backup import pre_migration_backup
from database.location import SOURCE_OVERRIDE, default_data_folder, resolve_location, write_pointer
from database.store import connect
from migration.registry import MIGRATIONS
from migration.runner import MigrationFailed, pending, run_pending, unknown_applied
from setup.env_file import write_env

OUTCOME_MOVE = "move"
OUTCOME_CURRENT = "current"
OUTCOME_EXISTING = "existing"
OUTCOME_MIGRATE = "migrate"


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


def check_foreign_database(path: Path) -> bool:
    """Raise FolderUnusable unless `path` is a Database this Dashboard can switch
    to; return True if it first needs migrating (Issue #200).

    Opened read-only on a plain connection, so nothing is written to it. A
    Database that predates `schema_migrations` reports every migration pending,
    so it counts as older. One recording a migration this code doesn't know was
    made by a newer version and is refused.
    """
    refusal = f"{path.name} in that folder isn't a Budgeting Tool Database"
    try:
        with closing(sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)) as connection:
            has_transactions = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'transactions'"
            ).fetchone()
            if has_transactions is None:
                raise FolderUnusable(refusal)
            behind = pending(connection, MIGRATIONS)
            ahead = unknown_applied(connection, MIGRATIONS)
    except sqlite3.DatabaseError as cause:  # not a SQLite file, or unreadable
        raise FolderUnusable(refusal) from cause
    if ahead:
        raise FolderUnusable(
            f"{path.name} was made by a newer version of the Dashboard. Update the tool first, then switch to it."
        )
    return bool(behind)


def backup_files(folder: Path, current_database: Path) -> list[Path]:
    """The downloaded Backups in `folder`, recognised by their default file name
    (`<name>-backup-<date>-<time>.db`, see `database_info.backup_file_name`)."""
    pattern = re.compile(rf"^.+-backup-\d{{8}}-\d{{6}}{re.escape(current_database.suffix)}$")
    return sorted(f for f in folder.iterdir() if f.is_file() and pattern.match(f.name))


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
    if not target.exists():
        backups = backup_files(folder, current_database)
        if len(backups) > 1:
            raise FolderUnusable(
                f"That folder holds {len(backups)} Backups ({', '.join(b.name for b in backups)}). "
                "Leave just one in the folder to switch to it."
            )
        if not backups:
            return FolderReport(folder, OUTCOME_MOVE, target)
        # A Backup saved under its default name: use that file as it is.
        target = backups[0]
    needs_migrating = check_foreign_database(target)
    return FolderReport(folder, OUTCOME_MIGRATE if needs_migrating else OUTCOME_EXISTING, target)


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
    data_folder: Path | None = None,
    write_pointer_file: Callable[[Path, Path], None] = write_pointer,
) -> list[Path]:
    """Carry out the confirmed choice of `chosen` as the Database's folder.

    The new location goes into `.env` (`write_location`) if a `DATABASE_PATH`
    override exists, otherwise into the pointer file in `data_folder`
    (`write_pointer_file`).

    Returns the old files a move could not delete (empty for any other outcome
    or a clean move), so the caller can tell the user they are still there."""
    report = inspect_folder(chosen, Path(handle.path), ensure_writable=ensure_writable)
    if report.outcome == OUTCOME_CURRENT:
        raise FolderUnusable("The Database is already in that folder")
    record = _Recorder(
        overridden=resolve_location(env_path=env_path, data_folder=data_folder).source == SOURCE_OVERRIDE,
        env_path=env_path,
        data_folder=data_folder,
        write_location=write_location,
        write_pointer_file=write_pointer_file,
    )
    if report.outcome in (OUTCOME_EXISTING, OUTCOME_MIGRATE):
        _switch(handle, report, record, open_store)
        return []
    return _move(handle, report, record, verify_copy, open_store)


@dataclass(frozen=True)
class _Recorder:
    """Records a new Database location where the resolver will look for it."""

    overridden: bool
    env_path: Path
    data_folder: Path | None
    write_location: Callable[[Path, dict[str, str]], None]
    write_pointer_file: Callable[[Path, Path], None]

    def save(self, target: Path) -> None:
        """Raise MoveFailed if it can't be written; the old record is then as it was."""
        if self.overridden:
            try:
                self.write_location(self.env_path, {"DATABASE_PATH": str(target)})
            except OSError as cause:
                raise MoveFailed(f"Couldn't update .env: {cause}") from cause
            return
        folder = default_data_folder() if self.data_folder is None else self.data_folder
        try:
            self.write_pointer_file(folder, target)
        except OSError as cause:
            raise MoveFailed(f"Couldn't save the new location: {cause}") from cause

    def apply_in_process(self, target: Path) -> None:
        """Make this process's own environment agree with what was saved."""
        if self.overridden:
            os.environ["DATABASE_PATH"] = str(target)


def _switch(handle, report, record, open_store) -> None:
    """Start using the Database already in the folder. Nothing is copied or
    overwritten, and the current Database stays exactly where it is. An older
    Database is migrated first, before the normal open (which would create
    tables and seed Categories in it); if anything after that fails, it is put
    back as it was."""
    copy = _migrate(report.target) if report.outcome == OUTCOME_MIGRATE else None
    new_store = None
    try:
        try:
            new_store = open_store(report.target)
        except Exception as cause:
            raise MoveFailed(f"Couldn't open {report.target.name}: {cause}") from cause
        # The location is saved only after the new connection opened; the swap comes last.
        record.save(report.target)
    except MoveFailed as failure:
        if new_store is not None:
            new_store.close()
        if copy is not None:
            _put_back(report.target, copy, str(failure))
        raise
    record.apply_in_process(report.target)
    # The old file is kept, so it is closed only to release it, not to delete it.
    handle.swap(new_store).close()


def _migrate(path: Path) -> Path:
    """Copy `path` to a `.pre-migration-` copy, then run the pending migrations
    on a plain connection - the order `python -m migration` uses. Returns the
    copy. If a migration fails, for any reason, the file is put back as it was
    and the copy removed."""
    with closing(sqlite3.connect(path)) as connection:
        try:
            copy = pre_migration_backup(connection, path)
        except (sqlite3.Error, OSError) as cause:
            raise MoveFailed(f"Couldn't copy {path.name} before migrating it: {cause}") from cause
        try:
            run_pending(connection, MIGRATIONS)
        except MigrationFailed as failure:
            reason = f"Migrating {path.name} failed at '{failure.name}': {failure.__cause__}."
        except Exception as failure:  # e.g. sqlite3.Error outside a migration's own step
            reason = f"Migrating {path.name} failed: {failure}."
        else:
            return copy
    _put_back(path, copy, reason)


def _put_back(path: Path, copy: Path, reason: str) -> None:
    """Restore `path` from its pre-migration `copy`, remove the copy, and raise
    MoveFailed saying `reason` - the file is as it was and nothing switched."""
    try:
        shutil.copyfile(copy, path)
    except OSError as cause:
        raise MoveFailed(
            f"{reason} {path.name} couldn't be put back; its pre-migration copy is {copy}: {cause}"
        ) from cause
    copy.unlink(missing_ok=True)
    raise MoveFailed(f"{reason} {path.name} was left as it was and the Dashboard stays on its current Database.")


def _move(handle, report, record, verify_copy, open_store) -> list[Path]:
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

        # The location is saved only now that the new connection opened, and
        # the live swap comes after it, so a failure up to here changes nothing.
        record.save(report.target)
        record.apply_in_process(report.target)
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
    return _remove(sources)


def _remove(files: list[Path]) -> list[Path]:
    """Delete `files`; return those that wouldn't go. The move has already
    succeeded (or is being rolled back), so a file that won't go is reported
    rather than failing it."""
    left_behind = []
    for file in files:
        try:
            file.unlink(missing_ok=True)
        except OSError:
            left_behind.append(file)
    return left_behind
