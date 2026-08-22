from datetime import date
from pathlib import Path

import openpyxl

from migration.legacy_config import COLUMNS, parse_legacy_config
from recurring.rules import RecurringRule


def _write_workbook(path: Path, rows: list[tuple]) -> None:
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(COLUMNS)
    for row in rows:
        worksheet.append(list(row))
    workbook.save(path)


def test_parse_legacy_config_remaps_a_salary_rule(tmp_path: Path):
    path = tmp_path / "recurring-transactions.xlsx"
    _write_workbook(
        path,
        [(4235.74, "Income", "Salary", "Fortnightly payment", "Weekly", 2, "Thursday", date(2026, 5, 7), None)],
    )

    rules = parse_legacy_config(path)

    assert rules == [
        RecurringRule(
            amount=4235.74,
            type="Income",
            category="Salary",
            notes="Fortnightly payment",
            frequency="Weekly",
            interval=2,
            day="Thursday",
            start_date=date(2026, 5, 7),
            end_date=None,
        )
    ]


def test_parse_legacy_config_remaps_debt_mortgage_repayment_to_debt(tmp_path: Path):
    path = tmp_path / "recurring-transactions.xlsx"
    _write_workbook(
        path,
        [(875, "Debt", "Mortgage Repayment", "Werribee", "Weekly", 2, "Thursday", date(2026, 5, 7), None)],
    )

    [rule] = parse_legacy_config(path)

    assert rule.type == "Debt"
    assert rule.category == "Mortgage Repayment"
    assert rule.notes == "Werribee"


def test_parse_legacy_config_remaps_bills_and_subscriptions_to_expense(tmp_path: Path):
    path = tmp_path / "recurring-transactions.xlsx"
    _write_workbook(
        path,
        [(37.5, "Bills & Subscriptions", "Subscriptions", "Gym", "Weekly", 2, "Friday", date(2026, 5, 8), None)],
    )

    [rule] = parse_legacy_config(path)

    assert rule.type == "Expense"
    assert rule.category == "Subscriptions"


def test_parse_legacy_config_skips_blank_rows(tmp_path: Path):
    path = tmp_path / "recurring-transactions.xlsx"
    _write_workbook(
        path,
        [
            (4235.74, "Income", "Salary", "Fortnightly payment", "Weekly", 2, "Thursday", date(2026, 5, 7), None),
            (None, None, None, None, None, None, None, None, None),
        ],
    )

    rules = parse_legacy_config(path)

    assert len(rules) == 1


def test_parse_legacy_config_parses_a_monthly_rule_with_an_end_date(tmp_path: Path):
    path = tmp_path / "recurring-transactions.xlsx"
    _write_workbook(
        path,
        [(100.0, "Expenses", "Groceries", "", "Monthly", 1, 15, date(2026, 1, 15), date(2026, 12, 31))],
    )

    [rule] = parse_legacy_config(path)

    assert rule.day == 15
    assert rule.end_date == date(2026, 12, 31)
