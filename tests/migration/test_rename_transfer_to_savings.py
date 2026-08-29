import sqlite3

from migration.rename_transfer_to_savings import migrate


def make_connection() -> sqlite3.Connection:
    """An in-memory database already on the category_id-based schema (Issue
    #90), with one Transfer-typed Category and its Transaction/Recurring Rule
    - what the live database looked like before ADR-0022's rename.
    """
    connection = sqlite3.connect(":memory:")
    connection.executescript(
        """
        CREATE TABLE categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            name TEXT NOT NULL UNIQUE,
            emoji TEXT,
            locked INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            notes TEXT NOT NULL
        );
        CREATE TABLE recurring_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            notes TEXT NOT NULL,
            frequency TEXT NOT NULL,
            interval INTEGER NOT NULL,
            day TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT
        );
        CREATE TABLE category_budgets (
            category_id INTEGER NOT NULL REFERENCES categories(id),
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            amount NUMERIC NOT NULL,
            PRIMARY KEY (category_id, year, month)
        );
        """
    )
    connection.execute("INSERT INTO categories (id, type, name) VALUES (346, 'Transfer', 'Savings')")
    connection.execute(
        "INSERT INTO transactions (date, amount, type, category_id, notes) "
        "VALUES ('2026-08-26', 1000.0, 'Transfer', 346, 'Aug')"
    )
    connection.execute(
        "INSERT INTO recurring_rules "
        "(amount, type, category_id, notes, frequency, interval, day, start_date, end_date) "
        "VALUES (100.0, 'Transfer', 346, 'To savings', 'Monthly', 1, '1', '2026-08-01', NULL)"
    )
    connection.commit()
    return connection


def test_migrate_renames_a_transfer_category_to_savings():
    connection = make_connection()

    migrate(connection)

    row = connection.execute("SELECT type, name FROM categories WHERE id = 346").fetchone()
    assert row == ("Savings", "Savings")


def test_migrate_renames_a_transfer_transaction_to_savings():
    connection = make_connection()

    migrate(connection)

    row = connection.execute("SELECT type FROM transactions WHERE category_id = 346").fetchone()
    assert row == ("Savings",)


def test_migrate_renames_a_transfer_recurring_rule_to_savings():
    connection = make_connection()

    migrate(connection)

    row = connection.execute("SELECT type FROM recurring_rules WHERE category_id = 346").fetchone()
    assert row == ("Savings",)


def test_migrate_is_safe_to_run_twice():
    connection = make_connection()

    migrate(connection)
    migrate(connection)

    row = connection.execute("SELECT type FROM categories WHERE id = 346").fetchone()
    assert row == ("Savings",)


def test_migrate_leaves_other_types_untouched():
    connection = make_connection()
    connection.execute("INSERT INTO categories (id, type, name) VALUES (1, 'Expense', 'Groceries')")
    connection.commit()

    migrate(connection)

    row = connection.execute("SELECT type FROM categories WHERE id = 1").fetchone()
    assert row == ("Expense",)
