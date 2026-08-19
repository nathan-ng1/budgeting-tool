import sqlite3
from datetime import date
from pathlib import Path

from database.store import connect
from statement_export.pipeline import Archive, run


def test_candidates_are_written_and_deduped_against_a_real_sqlite_store(make_candidate, tmp_path: Path):
    # End-to-end against database.store.LocalStore (not FakeStore) — no Google
    # Sheets API call, no .xlsx read, per ADR-0005/#23's acceptance criteria.
    store = connect(tmp_path / "budget.db")
    candidate = make_candidate(notes="Woolworths")

    first_run = run(candidates=[candidate], store=store, through=date(2026, 8, 5))
    assert first_run.to_write == [candidate]

    # A second run against the same database must dedupe the now-persisted row.
    second_run = run(candidates=[candidate], store=store, through=date(2026, 8, 5))
    assert second_run.to_write == []
    assert second_run.skipped == [candidate]


def test_due_recurring_rule_seeded_in_a_real_sqlite_store_is_expanded_and_written(tmp_path: Path):
    database_path = tmp_path / "budget.db"
    connect(database_path)  # creates the schema
    connection = sqlite3.connect(database_path)
    connection.execute(
        "INSERT INTO recurring_rules "
        "(amount, type, category, notes, frequency, interval, day, start_date, end_date) "
        "VALUES (5000.0, 'Income', 'Salary', 'Employer Pty Ltd', 'Monthly', 1, '5', '2026-08-05', NULL)"
    )
    connection.commit()
    connection.close()
    store = connect(database_path)

    result = run(candidates=[], store=store, through=date(2026, 8, 5))

    assert len(result.to_write) == 1
    assert result.to_write[0].notes == "Employer Pty Ltd"
    assert [row.notes for row in connect(database_path).read_existing_rows()] == ["Employer Pty Ltd"]


def test_candidates_are_written_and_source_file_is_archived(make_candidate, fake_store, tmp_path: Path):
    store = fake_store()
    source = tmp_path / "ANZ_20260730.csv"
    source.write_text("irrelevant — pipeline doesn't re-read this file")
    processed_dir = tmp_path / "processed"
    candidates = [make_candidate(notes="Woolworths")]

    result = run(
        candidates=candidates,
        store=store,
        through=date(2026, 8, 5),
        archive=Archive(source_path=source, processed_dir=processed_dir),
    )

    assert result.to_write == candidates
    assert store.appended == candidates
    assert not source.exists()
    assert (processed_dir / "ANZ_20260730.csv").exists()


def test_already_logged_candidate_is_not_reappended(make_candidate, make_existing_row, fake_store):
    store = fake_store(existing_rows=[make_existing_row(notes="Woolworths")])
    candidate = make_candidate(notes="Woolworths")

    result = run(
        candidates=[candidate],
        store=store,
        through=date(2026, 8, 5),
    )

    assert result.to_write == []
    assert store.appended == []


def test_no_source_file_still_writes_due_recurring_transactions(fake_store, make_rule):
    rule = make_rule(
        amount=5000.0,
        type="Income",
        category="Salary",
        notes="Employer Pty Ltd",
        frequency="Monthly",
        interval=1,
        day=5,
        start_date=date(2026, 8, 5),
    )
    store = fake_store(recurring_rules=[rule])

    result = run(
        candidates=[],
        store=store,
        through=date(2026, 8, 5),
    )

    assert len(result.to_write) == 1
    assert result.to_write[0].notes == "Employer Pty Ltd"
    assert store.appended == result.to_write


def test_no_source_path_given_does_not_touch_the_filesystem(make_candidate, fake_store):
    store = fake_store()

    result = run(
        candidates=[make_candidate()],
        store=store,
        through=date(2026, 8, 5),
    )

    assert len(result.to_write) == 1
