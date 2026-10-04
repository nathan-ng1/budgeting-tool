"""Applies pending one-off migrations, each at most once per database (Issue
#152, ADR-0025).

Which migrations have run is recorded in the database itself, in a
`schema_migrations` table this module owns - one row per applied migration,
keyed by its name. `pending`/`run_pending` work through a registry list in
its given order (see `migration.registry.MIGRATIONS`), never by discovering
files, so the order a migration runs in is explicit and reviewable.
"""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

TRACKING_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    name TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);
"""


@dataclass(frozen=True)
class Migration:
    name: str
    migrate: Callable[[sqlite3.Connection], None]


class MigrationFailed(Exception):
    """A migration raised - the run stopped there and it wasn't recorded as
    applied, so the next run retries it.
    """

    def __init__(self, name: str):
        super().__init__(f"Migration {name!r} failed")
        self.name = name


def pending(connection: sqlite3.Connection, migrations: list[Migration]) -> list[Migration]:
    applied = _applied_names(connection)
    return [migration for migration in migrations if migration.name not in applied]


def run_pending(connection: sqlite3.Connection, migrations: list[Migration]) -> list[str]:
    """Run every not-yet-applied migration in registry order, recording each
    as soon as it succeeds. Returns the names it ran.

    Stops at the first failure with MigrationFailed (chained to the original
    error). Migrations commit their own work, so a failure can leave earlier
    statements of that same migration committed - the caller backs the
    database up first (see `migration.__main__`).
    """
    applied: list[str] = []
    for migration in pending(connection, migrations):
        try:
            migration.migrate(connection)
        except Exception as error:
            connection.rollback()
            raise MigrationFailed(migration.name) from error
        _record(connection, [migration.name])
        applied.append(migration.name)
    return applied


def mark_all_applied(connection: sqlite3.Connection, migrations: list[Migration]) -> None:
    """Record every migration as applied without running it - for a brand new
    database, already built on the current schema, that none of them apply to.
    """
    _record(connection, [migration.name for migration in migrations])


def _applied_names(connection: sqlite3.Connection) -> set[str]:
    connection.executescript(TRACKING_SCHEMA)
    return {name for (name,) in connection.execute("SELECT name FROM schema_migrations")}


def _record(connection: sqlite3.Connection, names: list[str]) -> None:
    connection.executescript(TRACKING_SCHEMA)
    applied_at = datetime.now().isoformat(timespec="seconds")
    connection.executemany(
        "INSERT OR IGNORE INTO schema_migrations (name, applied_at) VALUES (?, ?)",
        [(name, applied_at) for name in names],
    )
    connection.commit()
