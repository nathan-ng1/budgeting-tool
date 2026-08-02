from datetime import date

from recurring.rules import RecurringRule
from transaction_log.writer import resolve_writes


def test_candidates_with_no_matching_existing_rows_are_all_written(
    make_candidate, fake_sheets_client
):
    candidates = [
        make_candidate(notes="Woolworths"),
        make_candidate(notes="Coles"),
    ]
    client = fake_sheets_client()

    result = resolve_writes(candidates, existing_rows=client.read_existing_rows())

    assert result.to_write == candidates
    assert result.skipped == []


def test_candidate_matching_existing_row_on_full_date_amount_and_notes_is_skipped(
    make_candidate, make_existing_row, fake_sheets_client
):
    candidate = make_candidate(notes="Woolworths")
    client = fake_sheets_client(existing_rows=[make_existing_row(notes="Woolworths")])

    result = resolve_writes([candidate], existing_rows=client.read_existing_rows())

    assert result.to_write == []
    assert result.skipped == [candidate]


def test_near_miss_on_amount_or_date_is_written_not_skipped(
    make_candidate, make_existing_row, fake_sheets_client
):
    different_amount = make_candidate(notes="Woolworths", amount=42.51)
    different_date = make_candidate(notes="Woolworths", date=date(2026, 8, 6))
    client = fake_sheets_client(existing_rows=[make_existing_row(notes="Woolworths")])

    result = resolve_writes(
        [different_amount, different_date], existing_rows=client.read_existing_rows()
    )

    assert result.to_write == [different_amount, different_date]
    assert result.skipped == []


def test_due_recurring_occurrence_already_in_log_is_merged_in_and_then_skipped(
    make_existing_row, fake_sheets_client
):
    salary_rule = RecurringRule(
        amount=5000.0,
        category="Income",
        sub_category="Salary",
        notes="Employer Pty Ltd",
        frequency="Monthly",
        interval=1,
        day=5,
        start_date=date(2026, 8, 5),
    )
    client = fake_sheets_client(
        existing_rows=[
            make_existing_row(date=date(2026, 8, 5), amount=5000.0, notes="Employer Pty Ltd")
        ]
    )

    result = resolve_writes(
        candidates=[],
        existing_rows=client.read_existing_rows(),
        recurring_rules=[salary_rule],
        through=date(2026, 8, 5),
    )

    assert result.to_write == []
    assert len(result.skipped) == 1
    assert result.skipped[0].notes == "Employer Pty Ltd"


def test_combined_candidates_and_recurring_occurrences_dedupe_as_one_unit(
    make_candidate, make_existing_row, fake_sheets_client
):
    new_candidate = make_candidate(notes="Woolworths", amount=42.50, date=date(2026, 8, 5))
    already_logged_candidate = make_candidate(notes="Coles", amount=15.00, date=date(2026, 8, 4))
    rent_rule = RecurringRule(
        amount=500.0,
        category="Income",
        sub_category="Rental",
        notes="Tenant Payment",
        frequency="Monthly",
        interval=1,
        day=1,
        start_date=date(2026, 8, 1),
    )
    client = fake_sheets_client(
        existing_rows=[
            make_existing_row(date=date(2026, 8, 4), amount=15.00, notes="Coles"),
            make_existing_row(date=date(2026, 8, 1), amount=500.0, notes="Tenant Payment"),
        ]
    )

    result = resolve_writes(
        candidates=[new_candidate, already_logged_candidate],
        existing_rows=client.read_existing_rows(),
        recurring_rules=[rent_rule],
        through=date(2026, 8, 5),
    )

    assert result.to_write == [new_candidate]
    assert {entry.notes for entry in result.skipped} == {"Coles", "Tenant Payment"}
