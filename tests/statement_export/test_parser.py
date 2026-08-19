from datetime import date
from pathlib import Path

import pytest

from statement_export.parser import RawTransaction, parse

# Covers a double-digit day/month row, a single-digit day/month row, and a
# positive-Amount (Bill Payment or Refund) row, in file order.
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
    # Positive-Amount rows (Bill Payment or Refund) now flow into categorisation
    # instead of being dropped at parse time — see ADR-0007.
    assert any(t.amount > 0 for t in transactions)
