"""Translation between the Budget tab's JSON shape and Category Budget reads/
writes - see Issues #62/#63.

Kept out of dashboard.server so the HTTP layer stays a router: what the
editor's rows look like on the wire is a question about the domain, not about
HTTP - mirrors dashboard.recurring.
"""

from dashboard.queries import BudgetEditorRow, BudgetGridRow
from transaction_log.categories import TYPE_ORDER

# Transfer has no Category Budget to set (CONTEXT.md's Category Budget entry),
# so it never appears as a section here.
BUDGETABLE_TYPES = tuple(t for t in TYPE_ORDER if t != "Transfer")

# The trailing window the Budget tab editor requests when its dropdown query
# param is absent - see dashboard.queries.TRAILING_WINDOWS.
DEFAULT_TRAILING_WINDOW = 3


def as_editor_payload(rows: list[BudgetEditorRow]) -> dict[str, list[dict]]:
    """Every Income/Expense/Debt Category grouped by Type, each carrying its
    current month's Category Budget (None if unset - unset != $0) alongside
    the grey historical context columns the editor shows beside it: last
    month's actual, a trailing average actual, and an average variance %
    (None when there isn't enough history to compute either - see
    dashboard.queries.get_budget_editor).
    """
    grouped: dict[str, list[dict]] = {transaction_type: [] for transaction_type in BUDGETABLE_TYPES}
    for row in rows:
        grouped[row.type].append(
            {
                "category": row.category,
                "amount": row.budgeted,
                "last_month_actual": row.last_month_actual,
                "trailing_average_actual": row.trailing_average_actual,
                "average_variance_pct": row.average_variance_pct,
            }
        )
    return grouped


def as_grid_payload(rows: list[BudgetGridRow]) -> dict[str, list[dict]]:
    """The Budget tab's Full year read-only grid (Issue #64), grouped by Type
    like as_editor_payload - each Category carries its 12 Category Budget
    amounts (None where unset) in the same July-to-June order the frontend's
    MonthSelector already renders month pills in, so the frontend can zip
    them together positionally rather than matching by (year, month).
    """
    grouped: dict[str, list[dict]] = {transaction_type: [] for transaction_type in BUDGETABLE_TYPES}
    for row in rows:
        grouped[row.type].append({"category": row.category, "amounts": row.amounts})
    return grouped


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
