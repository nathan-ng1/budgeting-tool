from datetime import date
from pathlib import Path

import pytest

from statement_export.parser import RawTransaction, parse

# Covers a double-digit day/month row, a single-digit day/month row, and a
# positive-Amount (Payment) row, in file order.
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
        RawTransaction(
            date=date(2026, 5, 4), amount=-40.0, notes="TRANSPORTFORNSW OPAL      CHIPPENDALE"
        ),
    ]


def test_parse_drops_positive_amount_rows(transactions: list[RawTransaction]):
    # Payments & Refunds (positive Amount) are dropped before categorisation —
    # never shown for Needs Review, never written. See CONTEXT.md.
    assert len(transactions) == 2
    assert all(t.amount < 0 for t in transactions)
    assert "PAYMENT - THANKYOU" not in [t.notes for t in transactions]
