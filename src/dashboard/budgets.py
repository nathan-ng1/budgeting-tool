"""Translation between the Budget tab's JSON shape and Category Budget reads/
writes - see Issue #62.

Kept out of dashboard.server so the HTTP layer stays a router: what the
editor's rows look like on the wire is a question about the domain, not about
HTTP - mirrors dashboard.recurring.
"""

from transaction_log.categories import CATEGORIES_BY_TYPE, TYPE_ORDER

# Transfer has no Category Budget to set (CONTEXT.md's Category Budget entry),
# so it never appears as a section here.
BUDGETABLE_TYPES = tuple(t for t in TYPE_ORDER if t != "Transfer")


def as_editor_payload(budgets: dict[str, float]) -> dict[str, list[dict]]:
    """Every Income/Expense/Debt Category grouped by Type, each carrying its
    Category Budget for whatever month `budgets` was read for - or None if
    that Category has no Category Budget set for the month (unset != $0).
    """
    return {
        transaction_type: [
            {"category": category, "amount": budgets.get(category)}
            for category in sorted(CATEGORIES_BY_TYPE[transaction_type])
        ]
        for transaction_type in BUDGETABLE_TYPES
    }


def amount_from_payload(payload) -> float:
    """The Amount a request body describes for one Category Budget write.

    Raises ValueError - with a message naming what's wrong - for anything the
    caller could fix by sending a different body.
    """
    if not isinstance(payload, dict) or "amount" not in payload:
        raise ValueError("Missing required field: amount")

    try:
        return float(payload["amount"])
    except (TypeError, ValueError):
        raise ValueError(f"Field 'amount' must be a number, got {payload['amount']!r}") from None
