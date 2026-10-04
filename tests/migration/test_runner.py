import sqlite3

import pytest

from migration.runner import Migration, MigrationFailed, mark_all_applied, pending, run_pending


def recording(name: str, calls: list[str]) -> Migration:
    """A Migration that just records its own name when it runs."""
    return Migration(name=name, migrate=lambda _connection: calls.append(name))


def failing(name: str) -> Migration:
    def migrate(_connection: sqlite3.Connection) -> None:
        raise RuntimeError("boom")

    return Migration(name=name, migrate=migrate)


def test_run_pending_runs_every_migration_in_registry_order():
    connection = sqlite3.connect(":memory:")
    calls: list[str] = []

    applied = run_pending(connection, [recording("b_second", calls), recording("a_first", calls)])

    assert calls == ["b_second", "a_first"]
    assert applied == ["b_second", "a_first"]


def test_run_pending_skips_an_already_applied_migration():
    connection = sqlite3.connect(":memory:")
    calls: list[str] = []
    run_pending(connection, [recording("first", calls)])
    calls.clear()

    applied = run_pending(connection, [recording("first", calls), recording("second", calls)])

    assert calls == ["second"]
    assert applied == ["second"]


def test_run_pending_records_applied_migrations_in_the_database_itself():
    connection = sqlite3.connect(":memory:")

    run_pending(connection, [recording("first", [])])

    assert pending(connection, [recording("first", [])]) == []


def test_a_failing_migration_stops_the_run_and_is_not_recorded_as_applied():
    connection = sqlite3.connect(":memory:")
    calls: list[str] = []
    migrations = [recording("first", calls), failing("broken"), recording("third", calls)]

    with pytest.raises(MigrationFailed) as excinfo:
        run_pending(connection, migrations)

    assert excinfo.value.name == "broken"
    assert calls == ["first"]
    assert [m.name for m in pending(connection, migrations)] == ["broken", "third"]


def test_mark_all_applied_leaves_nothing_pending():
    connection = sqlite3.connect(":memory:")
    calls: list[str] = []
    migrations = [recording("first", calls), recording("second", calls)]

    mark_all_applied(connection, migrations)

    assert pending(connection, migrations) == []
    assert run_pending(connection, migrations) == []
    assert calls == []


def test_mark_all_applied_is_safe_to_run_twice():
    connection = sqlite3.connect(":memory:")
    migrations = [recording("first", [])]

    mark_all_applied(connection, migrations)
    mark_all_applied(connection, migrations)

    assert pending(connection, migrations) == []
