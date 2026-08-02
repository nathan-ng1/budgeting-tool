from datetime import date
from pathlib import Path

import openpyxl

from recurring.config import COLUMNS, parse_config
from recurring.rules import RecurringRule


def test_parse_config_round_trips_a_rule(tmp_path: Path):
    path = tmp_path / "recurring-transactions.xlsx"
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(COLUMNS)
    worksheet.append(
        [4200.0, "Income", "Salary", "Employer Pty Ltd", "Monthly", 1, 15, date(2026, 1, 15), None]
    )
    workbook.save(path)

    rules = parse_config(path)

    assert rules == [
        RecurringRule(
            amount=4200.0,
            category="Income",
            sub_category="Salary",
            notes="Employer Pty Ltd",
            frequency="Monthly",
            interval=1,
            day=15,
            start_date=date(2026, 1, 15),
            end_date=None,
        )
    ]


def test_parse_config_skips_blank_rows(tmp_path: Path):
    path = tmp_path / "recurring-transactions.xlsx"
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(COLUMNS)
    worksheet.append([4200.0, "Income", "Salary", "Employer Pty Ltd", "Monthly", 1, 15, date(2026, 1, 15), None])
    worksheet.append([None] * len(COLUMNS))
    workbook.save(path)

    rules = parse_config(path)

    assert len(rules) == 1
