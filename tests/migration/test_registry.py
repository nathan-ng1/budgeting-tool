import sqlite3
from pathlib import Path

from database.store import open_connection
from migration.registry import MIGRATIONS
from migration.runner import pending


def test_registry_runs_the_existing_migrations_oldest_first():
    assert [m.name for m in MIGRATIONS] == [
        "categories_table",
        "rename_transfer_to_savings",
        "add_bills_and_subscriptions",
    ]


def test_a_brand_new_database_has_no_pending_migrations(tmp_path: Path):
    connection = open_connection(tmp_path / "budget.db")

    assert pending(connection, MIGRATIONS) == []


def test_an_existing_database_keeps_every_migration_pending(tmp_path: Path):
    database_path = tmp_path / "budget.db"
    # An install from before Issue #152: real tables, but no record of which
    # migrations it has had.
    existing = sqlite3.connect(database_path)
    existing.execute(
        "CREATE TABLE transactions (id INTEGER PRIMARY KEY, date TEXT NOT NULL, amount REAL NOT NULL, "
        "type TEXT NOT NULL, category_id INTEGER NOT NULL, notes TEXT NOT NULL)"
    )
    existing.commit()
    existing.close()

    connection = open_connection(database_path)

    assert pending(connection, MIGRATIONS) == MIGRATIONS


def test_reopening_a_brand_new_database_keeps_it_fully_migrated(tmp_path: Path):
    database_path = tmp_path / "budget.db"
    open_connection(database_path).close()

    connection = open_connection(database_path)

    assert pending(connection, MIGRATIONS) == []
