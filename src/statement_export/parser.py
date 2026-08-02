import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class RawTransaction:
    date: date
    amount: float  # signed — negative = spend, positive = payment/credit
    notes: str


def parse(path: Path) -> list[RawTransaction]:
    transactions = []
    with open(path, newline="") as f:
        for date_str, amount_str, notes in csv.reader(f):
            amount = float(amount_str)
            if amount > 0:
                # Payments & Refunds — dropped before categorisation, never
                # shown for Needs Review, never written. See CONTEXT.md.
                continue
            transactions.append(
                RawTransaction(
                    date=datetime.strptime(date_str, "%d/%m/%Y").date(),
                    amount=amount,
                    notes=notes.strip(),
                )
            )
    return transactions
