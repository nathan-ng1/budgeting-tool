"""Translation between the Transactions tab's JSON shape and Transaction/
Candidate - see Issues #33 and #35.

Kept out of dashboard.server so the HTTP layer stays a router: what a
Transaction looks like on the wire is a question about the domain, not about
HTTP - mirrors dashboard.recurring.
"""

import csv
import io
from datetime import date

from transaction_log.entries import Candidate, Transaction

FIELDS = ("date", "amount", "type", "category", "notes")
CSV_HEADER = ("Date", "Amount", "Type", "Category", "Notes")


def as_payload(transaction: Transaction) -> dict:
    return {
        "id": transaction.id,
        "date": transaction.date.isoformat(),
        "amount": transaction.amount,
        "type": transaction.type,
        "category": transaction.category,
        "notes": transaction.notes,
    }


def as_csv(transactions: list[Transaction]) -> bytes:
    """The Export panel's `.csv` (Issue #96) - the same 5 columns as the
    Transaction Log, header-only when `transactions` is empty, with no
    internal `id` since that's meaningless outside the Dashboard.
    """
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADER)
    for t in transactions:
        writer.writerow([t.date.isoformat(), t.amount, t.type, t.category, t.notes])
    return buffer.getvalue().encode("utf-8")


def from_payload(payload) -> Candidate:
    """The Candidate a request body describes.

    Raises ValueError - with a message naming what's wrong - for anything the
    caller could fix by sending a different body. Candidate's own
    __post_init__ raises the same way for a zero Amount or an invalid (Type,
    Category) pair, so the caller has one kind of error to handle.
    """
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object describing one transaction")

    missing = [field for field in FIELDS if field not in payload]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")

    return Candidate(
        date=_date(payload["date"], "date"),
        amount=_number(payload["amount"], "amount"),
        type=payload["type"],
        category=payload["category"],
        notes=payload["notes"],
    )


def _number(value, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Field {field!r} must be a number, got {value!r}") from None


def _date(value, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"Field {field!r} must be a date as YYYY-MM-DD, got {value!r}") from None
