from datetime import date, datetime
from pathlib import Path

import openpyxl

from migration.legacy_categories import remap_type_category
from recurring.rules import RecurringRule

COLUMNS = [
    "Amount",
    "Category",
    "Sub-Category",
    "Notes",
    "Frequency",
    "Interval",
    "Day",
    "Start Date",
    "End Date",
]


def parse_legacy_config(path: Path) -> list[RecurringRule]:
    """Parse the retired `config\\recurring-transactions.xlsx` format, remapped
    to the Type/Category model — see ADR-0005 and ADR-0006."""
    workbook = openpyxl.load_workbook(path, data_only=True)
    worksheet = workbook.active

    rules = []
    for row in worksheet.iter_rows(min_row=2, max_col=len(COLUMNS), values_only=True):
        if row[0] is None:
            continue

        amount, category, sub_category, notes, frequency, interval, day, start_date, end_date = row
        transaction_type, new_category = remap_type_category(category, sub_category)
        rules.append(
            RecurringRule(
                amount=float(amount),
                type=transaction_type,
                category=new_category,
                notes=notes or "",
                frequency=frequency,
                interval=int(interval),
                day=int(day) if frequency == "Monthly" else day,
                start_date=_to_date(start_date),
                end_date=_to_date(end_date) if end_date is not None else None,
            )
        )
    return rules


def _to_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise ValueError(f"Expected a date cell, got {value!r}")
