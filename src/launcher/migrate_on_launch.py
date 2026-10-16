"""The Retail launcher's migration policy (Issue #250, spec #236, decision S8).

On launch, pending migrations run after an automatic pre-migration backup. If
one fails, the backup is put back and a LaunchMigrationError says so, leaving
the Buyer's data exactly as it was. A Database written by a newer Version of
the app (one recording a migration this build doesn't know) is refused, never
migrated. The Collaborator Edition keeps its own policy - `dashboard.__main__`
refuses to start until `update` has run (ADR-0025); only *when* migrations run
differs, so the runner and `pre_migration_backup` are the shared ones.

Everything here uses a plain connection, before `open_connection` touches the
file (it builds missing tables and seeds Categories), so the backup really is
the Database as the Buyer left it.
"""

import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

from database.backup import pre_migration_backup
from migration.registry import MIGRATIONS
from migration.runner import Migration, MigrationFailed, pending, run_pending, unknown_applied


class LaunchMigrationError(Exception):
    """The Database can't be opened by this Version; the message is for the Buyer.

    The Database is left as it was: nothing ran, or the backup was restored."""


def migrate_on_launch(database_path: Path, migrations: list[Migration] = MIGRATIONS) -> list[str]:
    """Run the pending migrations on `database_path`, returning the names it ran.

    A Database that doesn't exist yet is brand new: the normal open builds it on
    the current schema and marks every migration applied, so there is nothing to
    back up or run.
    """
    if not database_path.exists():
        return []

    with closing(sqlite3.connect(database_path)) as connection:
        try:
            ahead = unknown_applied(connection, migrations)
            behind = pending(connection, migrations)
        except sqlite3.DatabaseError as cause:  # not a SQLite file, or unreadable
            raise LaunchMigrationError(
                f"{database_path.name} couldn't be read as a Budgeting Tool Database: {cause}."
            ) from cause
        if ahead:
            raise LaunchMigrationError(
                f"{database_path.name} was saved by a newer version of Budgeting Tool than this one. "
                "Install the latest version, then open it again. Nothing in your data was changed."
            )
        if not behind:
            return []
        try:
            backup = pre_migration_backup(connection, database_path)
        except (sqlite3.Error, OSError) as cause:
            raise LaunchMigrationError(
                f"Budgeting Tool couldn't back up {database_path.name} before updating it ({cause}), "
                "so it hasn't touched it. Nothing in your data was changed."
            ) from cause
        try:
            return run_pending(connection, migrations)
        except MigrationFailed as failure:
            reason = f"Updating your data failed at step '{failure.name}': {failure.__cause__}."
        except Exception as failure:  # e.g. sqlite3.Error outside a migration's own step
            reason = f"Updating your data failed: {failure}."

    # The connection is closed by now: Windows won't overwrite an open SQLite file.
    _put_back(database_path, backup, reason)


def _put_back(database_path: Path, backup: Path, reason: str) -> None:
    try:
        shutil.copyfile(backup, database_path)
    except OSError as cause:
        raise LaunchMigrationError(
            f"{reason} Your data couldn't be put back automatically ({cause}); "
            f"a copy from before the update is saved at {backup}."
        ) from cause
    backup.unlink(missing_ok=True)
    raise LaunchMigrationError(f"{reason} Your data has been put back exactly as it was; nothing was lost.")
