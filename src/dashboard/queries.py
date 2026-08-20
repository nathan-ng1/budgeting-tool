"""Pure query module computing the Dashboard's per-month Overview view-model.

No HTTP or browser dependency here - callable directly against any store
(LocalStore or FakeStore) so it's unit-testable on its own. See Issue #27.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date

from transaction_log.entries import Transaction


@dataclass(frozen=True)
class StatTiles:
    income: float
    expenses: float
    net_balance: float
    transferred: float


@dataclass(frozen=True)
class IncomeAllocation:
    expenses_amount: float
    expenses_pct: float
    transferred_amount: float
    transferred_pct: float
    remaining_amount: float
    remaining_pct: float
    over_income_amount: float
    over_income_pct: float


@dataclass(frozen=True)
class CategorySpend:
    category: str
    amount: float
    pct_of_expenses: float


@dataclass(frozen=True)
class BudgetVsActual:
    category: str
    expected: float | None
    actual: float
    diff: float | None
    pct: float | None


@dataclass(frozen=True)
class TopExpense:
    notes: str
    category: str
    date: str
    amount: float


@dataclass(frozen=True)
class DailyCumulative:
    date: str
    cumulative: float


@dataclass(frozen=True)
class ExpensesOverTime:
    daily: list[DailyCumulative]
    total: float
    daily_average: float


@dataclass(frozen=True)
class MonthOverview:
    year: int
    month: int
    stat_tiles: StatTiles
    income_allocation: IncomeAllocation
    spending_by_category: list[CategorySpend]
    budgeted_vs_actual: list[BudgetVsActual]
    top_expenses: list[TopExpense]
    expenses_over_time: ExpensesOverTime


def get_month_overview(store, year: int, month: int) -> MonthOverview:
    transactions = [t for t in store.read_transactions() if t.date.year == year and t.date.month == month]

    income = _round(sum(t.amount for t in transactions if t.type == "Income"))
    expenses = _round(sum(t.amount for t in transactions if t.type == "Expense"))
    transferred = _round(sum(t.amount for t in transactions if t.type == "Transfer"))
    net_balance = _round(income - expenses)

    return MonthOverview(
        year=year,
        month=month,
        stat_tiles=StatTiles(income=income, expenses=expenses, net_balance=net_balance, transferred=transferred),
        income_allocation=_income_allocation(income, expenses, transferred),
        spending_by_category=_spending_by_category(transactions, expenses),
        budgeted_vs_actual=_budgeted_vs_actual(transactions, store.read_category_budgets()),
        top_expenses=_top_expenses(transactions),
        expenses_over_time=_expenses_over_time(transactions, year, month),
    )


def _income_allocation(income: float, expenses: float, transferred: float) -> IncomeAllocation:
    if income <= 0:
        return IncomeAllocation(
            expenses_amount=expenses,
            expenses_pct=0.0,
            transferred_amount=transferred,
            transferred_pct=0.0,
            remaining_amount=0.0,
            remaining_pct=0.0,
            over_income_amount=0.0,
            over_income_pct=0.0,
        )

    remaining = income - expenses - transferred
    remaining_amount = max(remaining, 0.0)
    over_income_amount = max(-remaining, 0.0)

    return IncomeAllocation(
        expenses_amount=expenses,
        expenses_pct=_pct(expenses, income),
        transferred_amount=transferred,
        transferred_pct=_pct(transferred, income),
        remaining_amount=_round(remaining_amount),
        remaining_pct=_pct(remaining_amount, income),
        over_income_amount=_round(over_income_amount),
        over_income_pct=_pct(over_income_amount, income),
    )


def _expense_totals_by_category(transactions: list[Transaction]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for t in transactions:
        if t.type != "Expense":
            continue
        totals[t.category] = totals.get(t.category, 0.0) + t.amount
    return totals


def _spending_by_category(transactions: list[Transaction], expenses: float) -> list[CategorySpend]:
    totals = _expense_totals_by_category(transactions)

    rows = [
        CategorySpend(category=category, amount=_round(amount), pct_of_expenses=_pct(amount, expenses))
        for category, amount in totals.items()
        if amount != 0
    ]
    return sorted(rows, key=lambda row: (-row.amount, row.category))


def _budgeted_vs_actual(transactions: list[Transaction], category_budgets: dict[str, float]) -> list[BudgetVsActual]:
    actuals = _expense_totals_by_category(transactions)

    categories = set(category_budgets) | {c for c, amount in actuals.items() if amount != 0}

    rows = []
    for category in categories:
        expected = category_budgets.get(category)
        actual = _round(actuals.get(category, 0.0))
        # Positive diff = under budget (budget remaining); negative = overspent.
        diff = _round(expected - actual) if expected is not None else None
        pct = _pct(actual, expected) if expected is not None else None
        rows.append(BudgetVsActual(category=category, expected=expected, actual=actual, diff=diff, pct=pct))

    return sorted(rows, key=lambda row: row.category)


def _top_expenses(transactions: list[Transaction]) -> list[TopExpense]:
    expenses = [t for t in transactions if t.type == "Expense"]
    ranked = sorted(expenses, key=lambda t: (-t.amount, t.date, t.notes))
    return [
        TopExpense(notes=t.notes, category=t.category, date=t.date.isoformat(), amount=_round(t.amount))
        for t in ranked[:5]
    ]


def _expenses_over_time(transactions: list[Transaction], year: int, month: int) -> ExpensesOverTime:
    days_in_month = monthrange(year, month)[1]

    daily_totals: dict[date, float] = {}
    for t in transactions:
        if t.type != "Expense":
            continue
        daily_totals[t.date] = daily_totals.get(t.date, 0.0) + t.amount

    daily = []
    running_total = 0.0
    for day_number in range(1, days_in_month + 1):
        current_date = date(year, month, day_number)
        running_total += daily_totals.get(current_date, 0.0)
        daily.append(DailyCumulative(date=current_date.isoformat(), cumulative=_round(running_total)))

    total = _round(running_total)
    return ExpensesOverTime(daily=daily, total=total, daily_average=_round(total / days_in_month))


def _pct(part: float, whole: float | None) -> float:
    if not whole:
        return 0.0
    return _round(part / whole * 100, digits=1)


def _round(value: float, digits: int = 2) -> float:
    return round(value, digits)
