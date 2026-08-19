import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class RawTransaction:
    date: date
    amount: float  # signed — negative = spend, positive = Bill Payment or Refund
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
