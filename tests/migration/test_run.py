import csv
from datetime import date
from pathlib import Path

import openpyxl

from database.store import connect
from migration.legacy_config import COLUMNS as LEGACY_CONFIG_COLUMNS
from migration.run import migrate


def _write_transaction_log_csv(path: Path, rows: list[tuple]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "amount", "category", "sub_category", "notes"])
        writer.writerows(rows)


def _write_recurring_config_xlsx(path: Path, rows: list[tuple]) -> None:
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(LEGACY_CONFIG_COLUMNS)
    for row in rows:
        worksheet.append(list(row))
    workbook.save(path)


def test_migrate_writes_transactions_and_recurring_rules_to_a_real_sqlite_store(tmp_path: Path):
    transaction_log_csv = tmp_path / "transaction_log_export.csv"
    _write_transaction_log_csv(
        transaction_log_csv,
        [
            ("2026-07-30", "4235.74", "Income", "Salary", "Fortnightly payment"),
            ("2026-07-30", "875.00", "Debt", "Mortgage Repayment", "Werribee"),
        ],
    )
    recurring_config_xlsx = tmp_path / "recurring-transactions.xlsx"
    _write_recurring_config_xlsx(
        recurring_config_xlsx,
        [(4235.74, "Income", "Salary", "Fortnightly payment", "Weekly", 2, "Thursday", date(2026, 5, 7), None)],
    )
    store = connect(tmp_path / "budget.db")

    result = migrate(
        transaction_log_csv=transaction_log_csv,
        recurring_config_xlsx=recurring_config_xlsx,
        store=store,
    )

    assert len(result.transactions_written) == 2
    assert len(result.recurring_rules_written) == 1
    assert {row.notes for row in store.read_existing_rows()} == {"Fortnightly payment", "Werribee"}
    assert {r.category for r in store.read_recurring_rules()} == {"Salary"}


def test_migrate_skips_transactions_already_present_in_the_store(tmp_path: Path, make_candidate):
    transaction_log_csv = tmp_path / "transaction_log_export.csv"
    _write_transaction_log_csv(
        transaction_log_csv,
        [("2026-07-30", "4235.74", "Income", "Salary", "Fortnightly payment")],
    )
    recurring_config_xlsx = tmp_path / "recurring-transactions.xlsx"
    _write_recurring_config_xlsx(recurring_config_xlsx, [])
    store = connect(tmp_path / "budget.db")
    store.append_rows(
        [make_candidate(date=date(2026, 7, 30), amount=4235.74, type="Income", category="Salary", notes="Fortnightly payment")]
    )

    result = migrate(
        transaction_log_csv=transaction_log_csv,
        recurring_config_xlsx=recurring_config_xlsx,
        store=store,
    )

    assert result.transactions_written == []
    assert len(result.transactions_skipped) == 1
    assert len(store.read_existing_rows()) == 1


def test_migrate_skips_recurring_rules_already_present_in_the_store(tmp_path: Path, make_rule):
    transaction_log_csv = tmp_path / "transaction_log_export.csv"
    _write_transaction_log_csv(transaction_log_csv, [])
    recurring_config_xlsx = tmp_path / "recurring-transactions.xlsx"
    _write_recurring_config_xlsx(
        recurring_config_xlsx,
        [(4235.74, "Income", "Salary", "Fortnightly payment", "Weekly", 2, "Thursday", date(2026, 5, 7), None)],
    )
    existing_rule = make_rule(
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
    store = connect(tmp_path / "budget.db")
    store.append_recurring_rules([existing_rule])

    result = migrate(
        transaction_log_csv=transaction_log_csv,
        recurring_config_xlsx=recurring_config_xlsx,
        store=store,
    )

    assert result.recurring_rules_written == []
    assert store.read_recurring_rules() == [existing_rule]
