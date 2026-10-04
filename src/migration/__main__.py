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
from datetime import datetime
from pathlib import Path

from database.store import open_connection, resolve_database_path
from migration.registry import MIGRATIONS
from migration.runner import MigrationFailed, pending, run_pending


def backup(connection: sqlite3.Connection, database_path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = database_path.with_name(f"{database_path.stem}.pre-migration-{stamp}{database_path.suffix}")
    with sqlite3.connect(backup_path) as target:
        connection.backup(target)
    target.close()
    return backup_path


def main() -> int:
    database_path = resolve_database_path()
    connection = open_connection(database_path)

    if not pending(connection, MIGRATIONS):
        print("Database is up to date - no migrations to run.")
        return 0

    backup_path = backup(connection, database_path)
    print(f"Backed up the database to {backup_path}")

    try:
        for name in run_pending(connection, MIGRATIONS):
            print(f"Applied migration: {name}")
    except MigrationFailed as error:
        traceback.print_exception(error.__cause__, file=sys.stdout)
        print()
        print(f"Migration '{error.name}' failed - see above. Nothing after it was run.")
        print(f"Your database before migrating is saved at {backup_path}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
