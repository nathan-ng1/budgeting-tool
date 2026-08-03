from datetime import date
from pathlib import Path

import pytest

from beem.parser import categorise, parse
from statement_export.parser import RawTransaction

# Covers a double-digit day/month row, a single-digit day/month row, and a
# positive-Amount (incoming) row, in file order.
FIXTURE_BYTES = (
    b"30/07/2026,-15.5,mahjong + coke\n"
    b"13/07/2026,42.0,trip repayment\n"
    b"4/05/2026,-8.8,cake\n"
)


@pytest.fixture
def transactions(tmp_path: Path) -> list[RawTransaction]:
    csv_path = tmp_path / "Beem_20260730.csv"
    csv_path.write_bytes(FIXTURE_BYTES)
    return parse(csv_path)


def test_parse_reads_transactions_in_file_order_with_single_and_double_digit_dates(
    transactions: list[RawTransaction],
):
    assert transactions == [
        RawTransaction(date=date(2026, 7, 30), amount=-15.5, notes="mahjong + coke"),
        RawTransaction(date=date(2026, 7, 13), amount=42.0, notes="trip repayment"),
        RawTransaction(date=date(2026, 5, 4), amount=-8.8, notes="cake"),
    ]


def test_parse_does_not_drop_positive_amount_rows(transactions: list[RawTransaction]):
    # Unlike statement_export.parser.parse(), a positive amount here is a real
    # incoming Transaction, not a droppable Payments & Refunds credit.
    assert len(transactions) == 3
    assert any(t.amount > 0 for t in transactions)


def test_categorise_turns_positive_rows_into_income_beem_adjustment_candidates(make_candidate):
    positive = RawTransaction(date=date(2026, 7, 13), amount=42.0, notes="trip repayment")

    candidates, needs_categorisation = categorise([positive])

    assert candidates == [
        make_candidate(
            date=date(2026, 7, 13),
            amount=42.0,
            category="Income",
            sub_category="Beem Adjustment",
            notes="trip repayment",
        )
    ]
    assert needs_categorisation == []


def test_categorise_returns_negative_rows_for_downstream_categorisation():
    negative = RawTransaction(date=date(2026, 7, 30), amount=-15.5, notes="mahjong + coke")

    candidates, needs_categorisation = categorise([negative])

    assert candidates == []
    assert needs_categorisation == [negative]


def test_categorise_splits_a_mix_of_positive_and_negative_rows():
    positive = RawTransaction(date=date(2026, 7, 13), amount=42.0, notes="trip repayment")
    negative = RawTransaction(date=date(2026, 7, 30), amount=-15.5, notes="mahjong + coke")

    candidates, needs_categorisation = categorise([positive, negative])

    assert [c.notes for c in candidates] == ["trip repayment"]
    assert needs_categorisation == [negative]
