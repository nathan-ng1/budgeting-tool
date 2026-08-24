"""One-off migration onto Issue #90's `categories` table + `category_id` FKs.

Run once against a real pre-#90 database - one still holding `category` TEXT
columns on `transactions`/`recurring_rules`/`category_budgets` and no
`categories` table - not on every startup (mirrors `migration.run`'s own
one-off convention). A brand new database never needs this:
`database.store.connect()` already builds the target category_id-based schema
(and seeds `categories`) directly, so `migrate` is a no-op there. Safe to
re-run: each of the three tables is only rewritten while it still has its old
`category` TEXT column.
"""

import sqlite3

from database.store import SCHEMA, _seed_default_categories


def migrate(connection: sqlite3.Connection) -> None:
    # Additive - builds `categories` (and anything else missing) without
    # touching a `transactions`/`recurring_rules`/`category_budgets` table
    # that already exists under its old, pre-#90 shape.
    connection.executescript(SCHEMA)
    _seed_default_categories(connection)

    _migrate_table(
        connection,
        table="transactions",
        create="CREATE TABLE transactions_new ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, amount REAL NOT NULL, "
        "type TEXT NOT NULL, category_id INTEGER NOT NULL REFERENCES categories(id), notes TEXT NOT NULL)",
        copy="INSERT INTO transactions_new (id, date, amount, type, category_id, notes) "
        "SELECT old.id, old.date, old.amount, old.type, c.id, old.notes "
        "FROM transactions old JOIN categories c ON c.name = old.category",
    )
    _migrate_table(
        connection,
        table="recurring_rules",
        create="CREATE TABLE recurring_rules_new ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, amount REAL NOT NULL, type TEXT NOT NULL, "
        "category_id INTEGER NOT NULL REFERENCES categories(id), notes TEXT NOT NULL, "
        "frequency TEXT NOT NULL, interval INTEGER NOT NULL, day TEXT NOT NULL, "
        "start_date TEXT NOT NULL, end_date TEXT)",
        copy="INSERT INTO recurring_rules_new "
        "(id, amount, type, category_id, notes, frequency, interval, day, start_date, end_date) "
        "SELECT old.id, old.amount, old.type, c.id, old.notes, old.frequency, old.interval, "
        "old.day, old.start_date, old.end_date "
        "FROM recurring_rules old JOIN categories c ON c.name = old.category",
    )
    _migrate_table(
        connection,
        table="category_budgets",
        create="CREATE TABLE category_budgets_new ("
        "category_id INTEGER NOT NULL REFERENCES categories(id), year INTEGER NOT NULL, "
        "month INTEGER NOT NULL, amount NUMERIC NOT NULL, PRIMARY KEY (category_id, year, month))",
        copy="INSERT INTO category_budgets_new (category_id, year, month, amount) "
        "SELECT c.id, old.year, old.month, old.amount "
        "FROM category_budgets old JOIN categories c ON c.name = old.category",
    )
    connection.commit()


def _migrate_table(connection: sqlite3.Connection, table: str, create: str, copy: str) -> None:
    """Rewrite `table` from its old `category` TEXT column onto `category_id`
    via SQLite's standard create-new/copy/drop-old/rename-in dance - not a
    plain ALTER TABLE, since `category_budgets`' TEXT `category` column is
    part of its composite PRIMARY KEY (SQLite's ALTER TABLE DROP COLUMN
    refuses to drop a PRIMARY KEY column).

    A no-op if `table` doesn't have a `category` column any more - either
    it's already been migrated, or it was built directly against the
    category_id-based SCHEMA (a brand new database).
    """
    columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
    if "category" not in columns:
        return

    new_table = f"{table}_new"
    connection.execute(f"DROP TABLE IF EXISTS {new_table}")
    connection.execute(create)
    connection.execute(copy)
    connection.execute(f"DROP TABLE {table}")
    connection.execute(f"ALTER TABLE {new_table} RENAME TO {table}")
