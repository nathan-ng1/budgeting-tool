"""A consistent point-in-time copy of a Database made with SQLite's online
backup API (Issues #152, #197, ADR-0030) - safe on a live, open Database,
unlike a raw copy of the file, and it carries the migration record along."""

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path


def backup_to(connection: sqlite3.Connection, target_path: Path) -> None:
    with closing(sqlite3.connect(target_path)) as target:
        connection.backup(target)


def pre_migration_backup(connection: sqlite3.Connection, database_path: Path) -> Path:
    """Make a pre-migration copy (not a Backup - that is the downloaded file):
    `<name>.pre-migration-<timestamp>.db` beside the Database, for
    `python -m migration` and switching to an older Database (Issue #200)."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = database_path.with_name(f"{database_path.stem}.pre-migration-{stamp}{database_path.suffix}")
    backup_to(connection, backup_path)
    return backup_path
