import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class RawTransaction:
    date: date
    amount: float  # signed — negative = spend, positive = Bill Payment
    notes: str


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
) -> tuple[list[RawTransaction], list[RawTransaction]]:
    """Splits parsed rows into (dropped, to_categorise).

    A positive-Amount card row is unconditionally a Bill Payment - paying
    down the card balance rather than crediting a purchase back - and is
    dropped deterministically here, the same row-type-filtering shape as the
    Beem Report's own filtering (beem.parser.categorise). See ADR-0016.
    """
    dropped = []
    to_categorise = []
    for transaction in transactions:
        if transaction.amount > 0:
            dropped.append(transaction)
        else:
            to_categorise.append(transaction)
    return dropped, to_categorise
