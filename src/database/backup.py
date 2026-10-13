"""A consistent point-in-time copy of a Database made with SQLite's online
backup API (Issues #152, #197, ADR-0030) - safe on a live, open Database,
unlike a raw copy of the file, and it carries the migration record along."""

import sqlite3
from contextlib import closing
from pathlib import Path


def backup_to(connection: sqlite3.Connection, target_path: Path) -> None:
    with closing(sqlite3.connect(target_path)) as target:
        connection.backup(target)
