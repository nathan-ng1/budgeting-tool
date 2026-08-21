from dataclasses import dataclass
from pathlib import Path

from migration.historical import load_legacy_rows_from_csv, remap_transaction_log_rows
from migration.legacy_config import parse_legacy_config
from recurring.rules import RecurringRule
from transaction_log.entries import Candidate
from transaction_log.writer import resolve_writes


@dataclass(frozen=True)
class MigrationResult:
    transactions_written: list[Candidate]
    transactions_skipped: list[Candidate]
    recurring_rules_written: list[RecurringRule]
    recurring_rules_skipped: list[RecurringRule]


def migrate(transaction_log_csv: Path, recurring_config_xlsx: Path, store) -> MigrationResult:
    """One-off migration of the retired live Google Sheet's historical Transaction
    Log (exported to `transaction_log_csv`) and `config\\recurring-transactions.xlsx`
    into the local database — see ADR-0005. Safe to re-run: already-present rows on
    both sides are skipped rather than duplicated."""
    candidates = remap_transaction_log_rows(load_legacy_rows_from_csv(transaction_log_csv))
    write_result = resolve_writes(candidates=candidates, existing_rows=store.read_existing_rows())
    store.append_rows(write_result.to_write)

    legacy_rules = parse_legacy_config(recurring_config_xlsx)
    existing_rules = set(store.read_recurring_rules())
    rules_to_write = [r for r in legacy_rules if r not in existing_rules]
    rules_skipped = [r for r in legacy_rules if r in existing_rules]
    store.append_recurring_rules(rules_to_write)

    return MigrationResult(
        transactions_written=write_result.to_write,
        transactions_skipped=write_result.skipped,
        recurring_rules_written=rules_to_write,
        recurring_rules_skipped=rules_skipped,
    )
