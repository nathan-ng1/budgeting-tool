"""The add_goals migration (Goals spec section 3, ADR-0025), run against real
SQLite files shaped like an install from before Goals."""

import sqlite3
from pathlib import Path

import pytest

from migration.add_goals import migrate
from migration.registry import MIGRATIONS
from migration.runner import MigrationFailed, pending, run_pending

GOALS_EMOJI = "\N{DIRECT HIT}"

# The tables as they were before Goals: no `goals` table and no
# `transactions.goal_id`.
PRE_GOALS_SCHEMA = """
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, name TEXT NOT NULL UNIQUE,
    emoji TEXT, locked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, amount REAL NOT NULL,
    type TEXT NOT NULL, category_id INTEGER NOT NULL REFERENCES categories(id), notes TEXT NOT NULL
);
CREATE TABLE recurring_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT, amount REAL NOT NULL, type TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id), notes TEXT NOT NULL,
    frequency TEXT NOT NULL, interval INTEGER NOT NULL, day TEXT NOT NULL,
    start_date TEXT NOT NULL, end_date TEXT
);
INSERT INTO categories (type, name, locked) VALUES
    ('Income', 'Salary', 0), ('Expense', 'Groceries', 0), ('Expense', 'Beem Adjustment', 1),
    ('Savings', 'Savings', 0), ('Savings', 'Investments', 0);
INSERT INTO transactions (date, amount, type, category_id, notes)
    VALUES ('2026-08-05', 42.5, 'Expense', 2, 'Woolworths'), ('2026-08-06', 100.0, 'Savings', 4, 'Top-up');
"""


@pytest.fixture
def database(tmp_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(tmp_path / "budget.db")
    connection.executescript(PRE_GOALS_SCHEMA)
    connection.commit()
    yield connection
    connection.close()


def columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]


def goals_categories(connection: sqlite3.Connection) -> list[tuple]:
    return connection.execute(
        "SELECT type, name, emoji, locked FROM categories WHERE lower(name) = 'goals'"
    ).fetchall()


def test_the_migration_adds_the_goals_table_the_goal_link_column_and_the_locked_category(database):
    migrate(database)

    assert columns(database, "goals") == [
        "id", "title", "description", "target_amount", "start_date", "end_date", "state",
    ]
    assert "goal_id" in columns(database, "transactions")
    assert goals_categories(database) == [("Savings", "Goals", GOALS_EMOJI, 1)]


def test_the_migration_keeps_every_existing_transaction_and_category(database):
    transactions = database.execute("SELECT * FROM transactions ORDER BY id").fetchall()
    categories = database.execute("SELECT * FROM categories ORDER BY id").fetchall()

    migrate(database)

    after = database.execute(
        "SELECT id, date, amount, type, category_id, notes FROM transactions ORDER BY id"
    ).fetchall()
    assert after == transactions
    assert database.execute("SELECT goal_id FROM transactions").fetchall() == [(None,), (None,)]
    assert database.execute("SELECT * FROM categories WHERE id <= ? ORDER BY id", (len(categories),)).fetchall() == categories


def test_an_existing_empty_savings_category_called_goals_is_adopted_whatever_its_case(database):
    database.execute("INSERT INTO categories (type, name, locked) VALUES ('Savings', 'GOALS', 0)")
    database.commit()

    migrate(database)

    assert goals_categories(database) == [("Savings", "Goals", GOALS_EMOJI, 1)]


def test_an_existing_goals_category_with_transactions_fails_asking_for_a_rename(database):
    database.execute("INSERT INTO categories (type, name, locked) VALUES ('Savings', 'goals', 0)")
    database.execute(
        "INSERT INTO transactions (date, amount, type, category_id, notes) "
        "VALUES ('2026-08-07', 5.0, 'Savings', 6, 'Mine')"
    )
    database.commit()

    with pytest.raises(ValueError, match="(?i)rename") as caught:
        migrate(database)

    assert "'goals'" in str(caught.value)
    assert goals_categories(database) == [("Savings", "goals", None, 0)]


def test_an_existing_goals_category_with_a_recurring_rule_fails(database):
    database.execute("INSERT INTO categories (type, name, locked) VALUES ('Savings', 'Goals', 0)")
    database.execute(
        "INSERT INTO recurring_rules (amount, type, category_id, notes, frequency, interval, day, start_date) "
        "VALUES (50, 'Savings', 6, 'Monthly', 'Monthly', 1, '1', '2026-08-01')"
    )
    database.commit()

    with pytest.raises(ValueError, match="(?i)rename"):
        migrate(database)


def test_a_goals_category_under_another_type_fails_even_when_empty(database):
    database.execute("INSERT INTO categories (type, name, locked) VALUES ('Expense', 'Goals', 0)")
    database.commit()

    with pytest.raises(ValueError, match="(?i)rename"):
        migrate(database)


def test_a_rerun_after_the_migration_has_finished_changes_nothing(database):
    migrate(database)
    snapshot = database.execute("SELECT * FROM categories ORDER BY id").fetchall()

    migrate(database)

    assert database.execute("SELECT * FROM categories ORDER BY id").fetchall() == snapshot
    assert columns(database, "transactions").count("goal_id") == 1


def test_a_rerun_after_a_partial_failure_resumes_cleanly(database):
    # The first run got as far as the table and the column, then died before
    # the Category.
    database.execute("ALTER TABLE transactions ADD COLUMN goal_id INTEGER")
    database.execute(
        "CREATE TABLE goals (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT, "
        "target_amount REAL NOT NULL, start_date TEXT NOT NULL, end_date TEXT NOT NULL, "
        "state TEXT NOT NULL DEFAULT 'active')"
    )
    database.commit()

    migrate(database)

    assert goals_categories(database) == [("Savings", "Goals", GOALS_EMOJI, 1)]


def test_a_failed_clash_is_unrecorded_and_the_next_run_succeeds_once_renamed(database):
    database.execute("INSERT INTO categories (type, name, locked) VALUES ('Expense', 'Goals', 0)")
    database.commit()
    registry = [m for m in MIGRATIONS if m.name == "add_goals"]

    with pytest.raises(MigrationFailed):
        run_pending(database, registry)
    assert [m.name for m in pending(database, registry)] == ["add_goals"]

    database.execute("UPDATE categories SET name = 'Goal stuff' WHERE name = 'Goals'")
    database.commit()
    assert run_pending(database, registry) == ["add_goals"]
    assert pending(database, registry) == []


def test_add_goals_is_the_last_registered_migration():
    assert MIGRATIONS[-1].name == "add_goals"
