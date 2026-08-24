import sqlite3

from migration.categories_table import migrate
from transaction_log.categories import CATEGORIES_BY_TYPE

OLD_SCHEMA = """
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    amount REAL NOT NULL,
    type TEXT NOT NULL,
    category TEXT NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE recurring_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    type TEXT NOT NULL,
    category TEXT NOT NULL,
    notes TEXT NOT NULL,
    frequency TEXT NOT NULL,
    interval INTEGER NOT NULL,
    day TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT
);

CREATE TABLE category_budgets (
    category TEXT NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    amount NUMERIC NOT NULL,
    PRIMARY KEY (category, year, month)
);
"""


def make_pre_migration_connection() -> sqlite3.Connection:
    """An in-memory database in the pre-#90 shape: `category` TEXT columns,
    no `categories` table - what a real database looked like before this
    feature shipped.
    """
    connection = sqlite3.connect(":memory:")
    connection.executescript(OLD_SCHEMA)
    connection.commit()
    return connection


def test_migrate_seeds_categories_matching_categories_by_type():
    connection = make_pre_migration_connection()

    migrate(connection)

    rows = connection.execute("SELECT type, name FROM categories").fetchall()
    by_type: dict[str, set[str]] = {"Transfer": set()}
    for transaction_type, name in rows:
        by_type.setdefault(transaction_type, set()).add(name)
    assert by_type == CATEGORIES_BY_TYPE


def test_migrate_seeds_beem_adjustment_as_locked():
    connection = make_pre_migration_connection()

    migrate(connection)

    locked = connection.execute("SELECT locked FROM categories WHERE name = 'Beem Adjustment'").fetchone()[0]
    assert locked == 1


def test_migrate_seeds_every_other_category_as_unlocked():
    connection = make_pre_migration_connection()

    migrate(connection)

    rows = connection.execute("SELECT locked FROM categories WHERE name != 'Beem Adjustment'").fetchall()
    assert all(locked == 0 for (locked,) in rows)


def test_migrate_backfills_transaction_category_id_from_its_text_category():
    connection = make_pre_migration_connection()
    connection.execute(
        "INSERT INTO transactions (date, amount, type, category, notes) "
        "VALUES ('2026-08-05', 42.5, 'Expense', 'Groceries', 'Woolworths')"
    )
    connection.commit()

    migrate(connection)

    row = connection.execute(
        "SELECT t.date, t.amount, t.type, c.name, t.notes "
        "FROM transactions t JOIN categories c ON c.id = t.category_id"
    ).fetchone()
    assert row == ("2026-08-05", 42.5, "Expense", "Groceries", "Woolworths")


def test_migrate_backfills_recurring_rule_category_id_from_its_text_category():
    connection = make_pre_migration_connection()
    connection.execute(
        "INSERT INTO recurring_rules "
        "(amount, type, category, notes, frequency, interval, day, start_date, end_date) "
        "VALUES (100.0, 'Expense', 'Subscriptions', 'Streaming service', 'Weekly', 1, 'Wednesday', '2026-08-05', NULL)"
    )
    connection.commit()

    migrate(connection)

    row = connection.execute(
        "SELECT r.amount, r.type, c.name, r.notes FROM recurring_rules r JOIN categories c ON c.id = r.category_id"
    ).fetchone()
    assert row == (100.0, "Expense", "Subscriptions", "Streaming service")


def test_migrate_backfills_category_budget_category_id_from_its_text_category():
    connection = make_pre_migration_connection()
    connection.execute(
        "INSERT INTO category_budgets (category, year, month, amount) VALUES ('Groceries', 2026, 8, 500.0)"
    )
    connection.commit()

    migrate(connection)

    row = connection.execute(
        "SELECT c.name, cb.year, cb.month, cb.amount "
        "FROM category_budgets cb JOIN categories c ON c.id = cb.category_id"
    ).fetchone()
    assert row == ("Groceries", 2026, 8, 500.0)


def test_migrate_preserves_transaction_ids():
    connection = make_pre_migration_connection()
    connection.execute(
        "INSERT INTO transactions (id, date, amount, type, category, notes) "
        "VALUES (7, '2026-08-05', 42.5, 'Expense', 'Groceries', 'Woolworths')"
    )
    connection.commit()

    migrate(connection)

    [(transaction_id,)] = connection.execute("SELECT id FROM transactions").fetchall()
    assert transaction_id == 7


def test_migrate_is_safe_to_run_twice():
    connection = make_pre_migration_connection()
    connection.execute(
        "INSERT INTO transactions (date, amount, type, category, notes) "
        "VALUES ('2026-08-05', 42.5, 'Expense', 'Groceries', 'Woolworths')"
    )
    connection.commit()

    migrate(connection)
    migrate(connection)

    rows = connection.execute("SELECT date, amount, notes FROM transactions").fetchall()
    assert rows == [("2026-08-05", 42.5, "Woolworths")]
    names = [name for (name,) in connection.execute("SELECT name FROM categories")]
    assert len(names) == len(set(names))


def test_migrate_on_a_database_already_built_against_the_new_schema_is_a_noop():
    # database.store.connect() already builds the category_id-based schema
    # directly (Issue #90) - migrate() must not choke on a database that
    # never had the old `category` TEXT columns to begin with.
    from database.store import SCHEMA

    connection = sqlite3.connect(":memory:")
    connection.executescript(SCHEMA)
    connection.commit()

    migrate(connection)

    assert connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
