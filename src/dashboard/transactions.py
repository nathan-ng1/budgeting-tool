"""Translation between the Transactions tab's JSON shape and Transaction -
see Issue #33.

Kept out of dashboard.server so the HTTP layer stays a router: what a
Transaction looks like on the wire is a question about the domain, not about
HTTP - mirrors dashboard.recurring.
"""

from transaction_log.entries import Transaction


def as_payload(transaction: Transaction) -> dict:
    return {
        "id": transaction.id,
        "date": transaction.date.isoformat(),
        "amount": transaction.amount,
        "type": transaction.type,
        "category": transaction.category,
        "notes": transaction.notes,
    }
