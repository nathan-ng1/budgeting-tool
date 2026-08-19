import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from migration.legacy_categories import remap_type_category
from transaction_log.entries import Candidate


@dataclass(frozen=True)
class LegacyTransactionLogRow:
    date: date
    amount: float
    category: str
    sub_category: str
    notes: str


def load_legacy_rows_from_csv(path: Path) -> list[LegacyTransactionLogRow]:
    """Load a historical Transaction Log export snapshot (date, amount, category,
    sub_category, notes columns) fetched from the retired live Google Sheet — see
    ADR-0005."""
    with path.open(newline="", encoding="utf-8") as f:
        return [
            LegacyTransactionLogRow(
                date=date.fromisoformat(row["date"]),
                amount=float(row["amount"]),
                category=row["category"],
                sub_category=row["sub_category"],
                notes=row["notes"],
            )
            for row in csv.DictReader(f)
        ]


def remap_transaction_log_rows(rows: list[LegacyTransactionLogRow]) -> list[Candidate]:
    candidates = []
    for row in rows:
        transaction_type, category = remap_type_category(row.category, row.sub_category)
        candidates.append(
            Candidate(date=row.date, amount=row.amount, type=transaction_type, category=category, notes=row.notes)
        )
    return candidates
