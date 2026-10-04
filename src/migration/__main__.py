"""CLI seam `update.bat`/`update.command` shell out to after `uv sync`:
`python -m migration` runs every pending one-off migration against the user's
database (Issue #152, ADR-0025).

Thin plumbing around the tested `migration.runner` - keep decision logic out
of here. Backs the database file up next to itself before running anything,
since a migration that fails partway may already have committed some of its
work. Exits 1 on a failure so the update script can stop with a clear message.
"""

import sqlite3
import sys
import traceback
from contextlib import closing
from datetime import datetime
from pathlib import Path

from database.store import open_connection, resolve_database_path
from migration.registry import MIGRATIONS
from migration.runner import MigrationFailed, pending, run_pending


def backup(connection: sqlite3.Connection, database_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = database_path.with_name(f"{database_path.stem}.pre-migration-{stamp}{database_path.suffix}")
    with closing(sqlite3.connect(backup_path)) as target:
        connection.backup(target)
    return backup_path


def main() -> int:
    database_path = resolve_database_path()

    # Checked and backed up through a plain connection, before open_connection
    # touches the file (it builds missing tables and seeds `categories`), so
    # the backup really is the database as it was before this run. A database
    # that doesn't exist yet is brand new: open_connection marks every
    # migration applied there, so there's nothing to back up or run.
    if database_path.exists():
        with closing(sqlite3.connect(database_path)) as original:
            if not pending(original, MIGRATIONS):
                print("Database is up to date - no migrations to run.")
                return 0
            backup_path = backup(original, database_path)
        print(f"Backed up the database to {backup_path}")
    else:
        backup_path = None

    connection = open_connection(database_path)
    try:
        applied = run_pending(connection, MIGRATIONS)
    except MigrationFailed as error:
        traceback.print_exception(error.__cause__, file=sys.stdout)
        print()
        print(f"Migration '{error.name}' failed - see above. Nothing after it was run.")
        print(f"Your database before migrating is saved at {backup_path}")
        return 1

    for name in applied:
        print(f"Applied migration: {name}")
    if not applied:
        print("Database is up to date - no migrations to run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
