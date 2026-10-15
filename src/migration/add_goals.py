"""One-off migration delivering Goals (ADR-0031) to an existing install: the
`goals` table, the `transactions.goal_id` link column, and the locked Goals
Category under Savings.

Run once by `python -m migration` during the update process (ADR-0025). A
brand new Database is built on the current schema and never runs it. Three
guarded steps, in this order, so a rerun after a partial failure resumes
cleanly.
"""

import sqlite3

from transaction_log.categories import LOCKED_CATEGORIES

# Literals on purpose, not goals.links.GOALS_CATEGORY: a migration describes the
# schema as it was when it shipped, so renaming the app constant later must not
# change what this one-off does to an old database.
CATEGORY_NAME = "Goals"
CATEGORY_TYPE = "Savings"


def migrate(connection: sqlite3.Connection) -> None:
    # Created here, not left to SCHEMA: a database move runs migrations before
    # open_connection has applied SCHEMA to the file.
    connection.execute(
        "CREATE TABLE IF NOT EXISTS goals ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT, "
        "target_amount REAL NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL, "
        "state TEXT NOT NULL DEFAULT 'active')"
    )

    columns = {row[1] for row in connection.execute("PRAGMA table_info(transactions)")}
    if "goal_id" not in columns:
        connection.execute("ALTER TABLE transactions ADD COLUMN goal_id INTEGER")
    # Here, not in SCHEMA: SCHEMA also runs against old files, where the column
    # doesn't exist yet.
    connection.execute("CREATE INDEX IF NOT EXISTS idx_transactions_goal_id ON transactions(goal_id)")

    _ensure_goals_category(connection)
    connection.commit()


def _ensure_goals_category(connection: sqlite3.Connection) -> None:
    emoji = LOCKED_CATEGORIES[CATEGORY_NAME]

    # Case-insensitive in code: SQLite's lower() folds ASCII only.
    match = next(
        (
            row
            for row in connection.execute("SELECT id, type, name FROM categories")
            if row[2].strip().casefold() == CATEGORY_NAME.casefold()
        ),
        None,
    )

    if match is None:
        connection.execute(
            "INSERT INTO categories (type, name, emoji, locked) VALUES (?, ?, ?, 1)",
            (CATEGORY_TYPE, CATEGORY_NAME, emoji),
        )
        return

    category_id, category_type, name = match
    if category_type != CATEGORY_TYPE or _is_in_use(connection, category_id):
        raise ValueError(
            f"A Category called {name!r} already exists and Goals needs that name for its own locked "
            f"Savings Category. Rename {name!r} in Category Management (Settings), then run the update again."
        )

    connection.execute(
        "UPDATE categories SET name = ?, emoji = ?, locked = 1 WHERE id = ?",
        (CATEGORY_NAME, emoji, category_id),
    )


def _is_in_use(connection: sqlite3.Connection, category_id: int) -> bool:
    transactions, rules = connection.execute(
        "SELECT (SELECT COUNT(*) FROM transactions WHERE category_id = :id), "
        "(SELECT COUNT(*) FROM recurring_rules WHERE category_id = :id)",
        {"id": category_id},
    ).fetchone()
    return bool(transactions or rules)
