import csv
from datetime import date
from pathlib import Path

import pytest

from migration.historical import LegacyTransactionLogRow, load_legacy_rows_from_csv, remap_transaction_log_rows
from transaction_log.entries import Candidate


def _write_csv(path: Path, rows: list[tuple]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "amount", "category", "sub_category", "notes"])
        writer.writerows(rows)


def test_load_legacy_rows_from_csv_parses_every_column(tmp_path: Path):
    path = tmp_path / "export.csv"
    _write_csv(path, [("2026-07-30", "4235.74", "Income", "Salary", "Fortnightly payment")])

    rows = load_legacy_rows_from_csv(path)

    assert rows == [
        LegacyTransactionLogRow(
            date=date(2026, 7, 30),
            amount=4235.74,
            category="Income",
            sub_category="Salary",
            notes="Fortnightly payment",
        )
    ]


def test_remap_transaction_log_rows_maps_expenses_group_to_expense_type():
    rows = [
        LegacyTransactionLogRow(
            date=date(2026, 8, 3), amount=281.46, category="Expenses", sub_category="Holidays & Travel", notes="GG Getaway"
        )
    ]

    assert remap_transaction_log_rows(rows) == [
        Candidate(date=date(2026, 8, 3), amount=281.46, type="Expense", category="Holidays & Travel", notes="GG Getaway")
    ]


def test_remap_transaction_log_rows_maps_debt_mortgage_repayment_to_debt():
    rows = [
        LegacyTransactionLogRow(
            date=date(2026, 7, 30), amount=875.0, category="Debt", sub_category="Mortgage Repayment", notes="Werribee"
        )
    ]

    [candidate] = remap_transaction_log_rows(rows)

    assert candidate.type == "Debt"
    assert candidate.category == "Mortgage Repayment"


def test_remap_transaction_log_rows_preserves_row_count(tmp_path: Path):
    path = tmp_path / "export.csv"
    _write_csv(
        path,
        [
            ("2026-07-30", "4235.74", "Income", "Salary", "Fortnightly payment"),
            ("2026-07-30", "875.00", "Debt", "Mortgage Repayment", "Werribee"),
            ("2026-07-31", "37.50", "Bills & Subscriptions", "Subscriptions", "Gym"),
        ],
    )

    candidates = remap_transaction_log_rows(load_legacy_rows_from_csv(path))

    assert len(candidates) == 3
