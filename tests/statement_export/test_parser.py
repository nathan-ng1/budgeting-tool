from datetime import date
from pathlib import Path

import pytest

from statement_export.parser import RawTransaction, categorise, parse

# Covers a double-digit day/month row, a single-digit day/month row, and a
# positive-Amount (Bill Payment) row, in file order.
FIXTURE_BYTES = (
    b"30/07/2026,-4.95,KFC NORTHMEAD             NORTHMEAD\n"
    b"13/07/2026,2143.68,PAYMENT - THANKYOU\n"
    b"4/05/2026,-40,TRANSPORTFORNSW OPAL      CHIPPENDALE\n"
)


@pytest.fixture
def transactions(tmp_path: Path) -> list[RawTransaction]:
    csv_path = tmp_path / "ANZ_20260730.csv"
    csv_path.write_bytes(FIXTURE_BYTES)
    return parse(csv_path)


def test_parse_reads_transactions_in_file_order_with_single_and_double_digit_dates(
    transactions: list[RawTransaction],
):
    assert transactions == [
        RawTransaction(
            date=date(2026, 7, 30), amount=-4.95, notes="KFC NORTHMEAD             NORTHMEAD"
        ),
        RawTransaction(date=date(2026, 7, 13), amount=2143.68, notes="PAYMENT - THANKYOU"),
        RawTransaction(
            date=date(2026, 5, 4), amount=-40.0, notes="TRANSPORTFORNSW OPAL      CHIPPENDALE"
        ),
    ]


def test_parse_keeps_positive_amount_rows(transactions: list[RawTransaction]):
    # parse() itself doesn't filter - categorise() is what deterministically
    # drops positive-Amount rows below.
    assert any(t.amount > 0 for t in transactions)


def test_categorise_drops_positive_amount_rows():
    # ADR-0016 - every positive-Amount card row is unconditionally a Bill
    # Payment, dropped deterministically rather than sent to categorisation.
    positive = RawTransaction(date=date(2026, 7, 13), amount=2143.68, notes="PAYMENT - THANKYOU")

    dropped, to_categorise = categorise([positive])

    assert dropped == [positive]
    assert to_categorise == []


def test_categorise_routes_negative_amount_rows_to_categorisation():
    negative = RawTransaction(
        date=date(2026, 7, 30), amount=-4.95, notes="KFC NORTHMEAD             NORTHMEAD"
    )

    dropped, to_categorise = categorise([negative])

    assert dropped == []
    assert to_categorise == [negative]


def test_categorise_splits_a_mix_of_positive_and_negative_rows(transactions: list[RawTransaction]):
    dropped, to_categorise = categorise(transactions)

    assert [t.notes for t in dropped] == ["PAYMENT - THANKYOU"]
    assert [t.amount for t in to_categorise] == [-4.95, -40.0]
