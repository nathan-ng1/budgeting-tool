"""The Retail launcher's migrate-on-launch policy (Issue #250, spec #236, decision
S8): pending migrations run after an automatic pre-migration backup; a failure
puts the backup back byte-for-byte; a Database from a newer Version is refused.

Driven against real SQLite files with a small hand-made registry, so what is
under test is the policy, not any particular shipped migration.
"""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from launcher.migrate_on_launch import LaunchMigrationError, migrate_on_launch
from migration.runner import Migration, run_pending


def add_column(name: str) -> Migration:
    def migrate(connection: sqlite3.Connection) -> None:
        connection.execute(f"ALTER TABLE things ADD COLUMN {name} TEXT")
        connection.commit()

    return Migration(name=f"add_{name}", migrate=migrate)


def database_with_a_row(path: Path, applied: list[Migration] = ()) -> Path:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE TABLE things (id INTEGER PRIMARY KEY, label TEXT)")
        connection.execute("INSERT INTO things (label) VALUES ('keep me')")
        connection.commit()
        run_pending(connection, list(applied))
    return path


def columns(path: Path) -> list[str]:
    with closing(sqlite3.connect(path)) as connection:
        return [row[1] for row in connection.execute("PRAGMA table_info(things)")]


def pre_migration_files(path: Path) -> list[Path]:
    return sorted(path.parent.glob(f"{path.stem}.pre-migration-*{path.suffix}"))


def test_pending_migrations_are_backed_up_then_applied(tmp_path):
    path = database_with_a_row(tmp_path / "budget.db")

    applied = migrate_on_launch(path, [add_column("colour")])

    assert applied == ["add_colour"]
    assert "colour" in columns(path)
    (backup,) = pre_migration_files(path)
    assert "colour" not in columns(backup)


def test_nothing_pending_changes_nothing_and_makes_no_backup(tmp_path):
    migration = add_column("colour")
    path = database_with_a_row(tmp_path / "budget.db", applied=[migration])
    before = path.read_bytes()

    assert migrate_on_launch(path, [migration]) == []

    assert path.read_bytes() == before
    assert pre_migration_files(path) == []


def test_a_database_that_does_not_exist_yet_is_left_for_the_normal_open(tmp_path):
    path = tmp_path / "budget.db"

    assert migrate_on_launch(path, [add_column("colour")]) == []

    assert not path.exists()


def test_a_failing_migration_restores_the_backup_byte_for_byte(tmp_path):
    path = database_with_a_row(tmp_path / "budget.db")
    seen_by_the_failing_migration: dict[str, bytes] = {}

    def breaks_halfway(connection: sqlite3.Connection) -> None:
        # By now the backup exists on disk; remember it, then half-do the work.
        (backup,) = pre_migration_files(path)
        seen_by_the_failing_migration["backup"] = backup.read_bytes()
        connection.execute("ALTER TABLE things ADD COLUMN partial TEXT")
        connection.execute("DELETE FROM things")
        connection.commit()
        raise RuntimeError("boom")

    with pytest.raises(LaunchMigrationError) as failed:
        migrate_on_launch(path, [add_column("colour"), Migration("breaks", breaks_halfway)])

    assert path.read_bytes() == seen_by_the_failing_migration["backup"]
    assert columns(path) == ["id", "label"]
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("SELECT label FROM things").fetchall() == [("keep me",)]
    assert "breaks" in str(failed.value)
    assert "boom" in str(failed.value)
    assert pre_migration_files(path) == []


def test_a_failure_that_comes_with_no_migration_name_still_restores(tmp_path):
    path = database_with_a_row(tmp_path / "budget.db")

    def corrupts(connection: sqlite3.Connection) -> None:
        connection.execute("DROP TABLE things")
        connection.commit()
        raise sqlite3.OperationalError("disk I/O error")

    with pytest.raises(LaunchMigrationError):
        migrate_on_launch(path, [Migration("corrupts", corrupts)])

    assert columns(path) == ["id", "label"]


def test_a_database_from_a_newer_version_is_refused_and_left_untouched(tmp_path):
    from_the_future = Migration("from_the_future", lambda connection: None)
    path = database_with_a_row(tmp_path / "budget.db", applied=[from_the_future])
    before = path.read_bytes()

    with pytest.raises(LaunchMigrationError) as refused:
        migrate_on_launch(path, [add_column("colour")])

    assert "newer" in str(refused.value).lower()
    assert path.read_bytes() == before
    assert pre_migration_files(path) == []


def test_a_file_that_is_not_a_database_is_reported_not_crashed_on(tmp_path):
    path = tmp_path / "budget.db"
    path.write_text("this is not sqlite, just some text " * 20)

    with pytest.raises(LaunchMigrationError):
        migrate_on_launch(path, [add_column("colour")])

    assert pre_migration_files(path) == []
