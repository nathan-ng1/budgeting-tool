import sqlite3
from pathlib import Path

from database.store import open_connection
from migration.registry import MIGRATIONS
from migration.runner import pending, run_pending


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


def test_a_pre_categories_table_database_runs_every_migration_cleanly(tmp_path: Path):
    database_path = tmp_path / "budget.db"
    # An install from before Issue #90: `category` TEXT columns and no
    # `categories` table yet.
    existing = sqlite3.connect(database_path)
    existing.executescript(
        """
        CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
            amount REAL NOT NULL, type TEXT NOT NULL, category TEXT NOT NULL, notes TEXT NOT NULL);
        CREATE TABLE recurring_rules (id INTEGER PRIMARY KEY AUTOINCREMENT, amount REAL NOT NULL,
            type TEXT NOT NULL, category TEXT NOT NULL, notes TEXT NOT NULL, frequency TEXT NOT NULL,
            interval INTEGER NOT NULL, day TEXT NOT NULL, start_date TEXT NOT NULL, end_date TEXT);
        CREATE TABLE category_budgets (category TEXT NOT NULL, year INTEGER NOT NULL,
            month INTEGER NOT NULL, amount NUMERIC NOT NULL, PRIMARY KEY (category, year, month));
        INSERT INTO transactions (date, amount, type, category, notes)
            VALUES ('2026-08-05', 42.5, 'Expense', 'Groceries', 'Woolworths');
        """
    )
    existing.commit()
    existing.close()
    connection = open_connection(database_path)

    run_pending(connection, MIGRATIONS)

    assert pending(connection, MIGRATIONS) == []
    row = connection.execute(
        "SELECT t.type, c.name FROM transactions t JOIN categories c ON c.id = t.category_id"
    ).fetchone()
    assert row == ("Expense", "Groceries")
