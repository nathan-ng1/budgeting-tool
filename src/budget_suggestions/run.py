from datetime import date, datetime

from advisor.interface import Advisor, CategoryHistory
from dashboard.budgets import DEFAULT_TRAILING_WINDOW
from dashboard.queries import get_budget_editor


def generate_budget_suggestion(
    store, advisor: Advisor, today: date | None = None, trailing_months: int = DEFAULT_TRAILING_WINDOW
) -> str:
    """Analyse recent Expense/Debt Budgeted-vs-Actual history via `advisor`
    and store the resulting write-up as the one standing Budget Suggestion,
    replacing whatever was stored before (ADR-0014). Returns the write-up.

    Reuses dashboard.queries.get_budget_editor - the same historical/trailing-
    window helper the Budget tab's editor uses (Issue #63) - anchored on
    `today`'s month, rather than duplicating that windowing logic here.
    Income and Savings rows are dropped before the Advisor ever sees them
    (CONTEXT.md's Budget Suggestion entry: under/over-earning isn't advised
    on, and ADR-0023 explicitly kept Savings out of this write-up when it
    extended Category Budget to cover it).
    """
    today = today if today is not None else date.today()
    rows = get_budget_editor(store, today.year, today.month, trailing_months)
    history = [
        CategoryHistory(
            type=row.type,
            category=row.category,
            last_month_actual=row.last_month_actual,
            last_month_budgeted=row.last_month_budgeted,
            trailing_average_actual=row.trailing_average_actual,
            average_variance_pct=row.average_variance_pct,
        )
        for row in rows
        if row.type not in ("Income", "Savings")
    ]

    result = advisor.advise(history)
    store.write_budget_suggestion(result.write_up, datetime.now())
    return result.write_up
