import csv
from datetime import datetime
from pathlib import Path

from statement_export.parser import RawTransaction
from transaction_log.entries import Candidate


def parse(path: Path) -> list[RawTransaction]:
    transactions = []
    with open(path, newline="") as f:
        for date_str, amount_str, notes in csv.reader(f):
            transactions.append(
                RawTransaction(
                    date=datetime.strptime(date_str, "%d/%m/%Y").date(),
                    amount=float(amount_str),
                    notes=notes.strip(),
                )
            )
    return transactions


def categorise(
    transactions: list[RawTransaction],
) -> tuple[list[Candidate], list[RawTransaction]]:
    candidates = []
    needs_categorisation = []
    for transaction in transactions:
        if transaction.amount > 0:
            candidates.append(
                Candidate(
                    date=transaction.date,
                    amount=transaction.amount,
                    type="Income",
                    category="Beem Adjustment",
                    notes=transaction.notes,
                )
            )
        else:
            needs_categorisation.append(transaction)
    return candidates, needs_categorisation
