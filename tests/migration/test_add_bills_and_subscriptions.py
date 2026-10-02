import sqlite3

from database.store import SCHEMA
from migration.add_bills_and_subscriptions import migrate

PREDEFINED = {"Insurance", "Car Registration", "Phone Plan", "Internet"}


def make_connection() -> sqlite3.Connection:
    """An in-memory database on the current schema, seeded with a few
    pre-#147 Categories and no Bills & Subscriptions Type at all - what an
    existing install looks like before this migration, since
    `_seed_default_categories` never reseeds a non-empty `categories` table.
    """
    connection = sqlite3.connect(":memory:")
    connection.executescript(SCHEMA)
    connection.executemany(
        "INSERT INTO categories (type, name, locked) VALUES (?, ?, ?)",
        [
            ("Income", "Salary", 0),
            ("Expense", "Groceries", 0),
            ("Expense", "Beem Adjustment", 1),
            ("Savings", "Savings", 0),
        ],
    )
    connection.commit()
    return connection


def bills_and_subscriptions(connection: sqlite3.Connection) -> list[tuple[str, int]]:
    return connection.execute(
        "SELECT name, locked FROM categories WHERE type = 'Bills & Subscriptions' ORDER BY name"
    ).fetchall()


def test_migrate_seeds_exactly_the_four_predefined_categories_unlocked():
    connection = make_connection()

    migrate(connection)

    rows = bills_and_subscriptions(connection)
    assert {name for name, _locked in rows} == PREDEFINED
    assert all(locked == 0 for _name, locked in rows)


def test_migrate_is_safe_to_run_twice():
    connection = make_connection()

    migrate(connection)
    migrate(connection)

    assert len(bills_and_subscriptions(connection)) == len(PREDEFINED)


def test_migrate_leaves_every_other_type_and_category_untouched():
    connection = make_connection()
    before = connection.execute(
        "SELECT id, type, name, emoji, locked FROM categories ORDER BY id"
    ).fetchall()

    migrate(connection)

    after = connection.execute(
        "SELECT id, type, name, emoji, locked FROM categories "
        "WHERE type != 'Bills & Subscriptions' ORDER BY id"
    ).fetchall()
    assert after == before


def test_migrate_keeps_a_users_own_same_named_category_under_its_existing_type():
    # Category names are unique across every Type, so a user who already
    # created e.g. an Expense "Internet" keeps it as-is - the migration never
    # retypes or duplicates it, it just skips that one name.
    connection = make_connection()
    connection.execute("INSERT INTO categories (type, name) VALUES ('Expense', 'Internet')")
    connection.commit()

    migrate(connection)

    assert connection.execute("SELECT type FROM categories WHERE name = 'Internet'").fetchall() == [("Expense",)]
    assert {name for name, _locked in bills_and_subscriptions(connection)} == PREDEFINED - {"Internet"}


def test_a_rerun_does_not_bring_back_a_renamed_or_deleted_predefined_category():
    # Same reasoning as _seed_default_categories (Issue #144's fix): once the
    # Type has any Categories, a rerun can't tell "never created" from
    # "deliberately renamed/deleted", so it leaves the Type alone entirely.
    connection = make_connection()
    migrate(connection)
    connection.execute("UPDATE categories SET name = 'Car Insurance' WHERE name = 'Insurance'")
    connection.execute("DELETE FROM categories WHERE name = 'Phone Plan'")
    connection.commit()

    migrate(connection)

    names = {name for name, _locked in bills_and_subscriptions(connection)}
    assert names == {"Car Insurance", "Car Registration", "Internet"}
