"""One-off migration adding the Bills & Subscriptions Type's predefined
Categories to an existing database (Issue #147, ADR-0024).

Run once against a real pre-#147 database by `python -m migration` during
the update process (ADR-0025) - not on every connect(). A brand new
database never needs this: `database.store._seed_default_categories` already
seeds every CATEGORIES_BY_TYPE entry into an empty `categories` table, but by
design never reseeds a non-empty one, so an existing install can't pick the
new Type up any other way.

Safe to re-run: it only seeds while the Type has no Categories at all. Once
it has any, a rerun can't tell "never created" from "deliberately renamed or
deleted via Category Management" (the same reasoning as
`_seed_default_categories`), so it leaves the Type alone. A predefined name
that already exists under another Type - Category names are unique across
every Type - is skipped rather than retyped or duplicated.
"""

import sqlite3

from transaction_log.categories import CATEGORIES_BY_TYPE

TYPE = "Bills & Subscriptions"


def migrate(connection: sqlite3.Connection) -> None:
    [(count,)] = connection.execute("SELECT COUNT(*) FROM categories WHERE type = ?", (TYPE,))
    if count > 0:
        return

    connection.executemany(
        "INSERT OR IGNORE INTO categories (type, name, locked) VALUES (?, ?, 0)",
        [(TYPE, name) for name in sorted(CATEGORIES_BY_TYPE[TYPE])],
    )
    connection.commit()

