"""One-off migration renaming the Transfer Type to Savings (Issue #130,
ADR-0022).

Run once against a real pre-rename database still holding rows typed
'Transfer' - not on every connect() (mirrors `migration.categories_table`'s
own one-off convention). A brand new database never needs this: Savings
never existed under its old name there. Safe to re-run: each UPDATE only
touches rows still typed 'Transfer', so a second run is a no-op.
"""

import sqlite3


def migrate(connection: sqlite3.Connection) -> None:
    connection.execute("UPDATE categories SET type = 'Savings' WHERE type = 'Transfer'")
    connection.execute("UPDATE transactions SET type = 'Savings' WHERE type = 'Transfer'")
    connection.execute("UPDATE recurring_rules SET type = 'Savings' WHERE type = 'Transfer'")
    # category_budgets has no `type` column of its own - a Category Budget's
    # Type is derived from its category_id -> categories.type, already
    # migrated above, so there's nothing further to rewrite here.
    connection.commit()
