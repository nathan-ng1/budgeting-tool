"""Pure query module computing the Dashboard's Overview view-models - the
per-month Overview and the Full year Overview (see ADR-0011).

No HTTP or browser dependency here - callable directly against any store
(LocalStore or FakeStore) so it's unit-testable on its own. See Issue #27.
"""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date

from transaction_log.categories import TYPE_ORDER, Category, categories_by_type, type_lookup
from transaction_log.entries import Transaction

# The Types a Category Budget can apply to - Savings has none to budget
# (CONTEXT.md's Category Budget entry).
BUDGETABLE_TYPES = {"Income", "Expense", "Debt"}

# The trailing window sizes the Budget tab's editor dropdown offers - Issue #63.
TRAILING_WINDOWS = (3, 6, 12)


@dataclass(frozen=True)
class StatTiles:
    income: float
    expenses: float
    debt: float
    net_balance: float
    saved: float


@dataclass(frozen=True)
class IncomeAllocation:
    expenses_amount: float
    expenses_pct: float
    debt_amount: float
    debt_pct: float
    saved_amount: float
    saved_pct: float
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
    type: str
    category: str
    budgeted: float | None
    actual: float
    diff: float | None
    pct: float | None


@dataclass(frozen=True)
class BudgetEditorRow:
    type: str
    category: str
    budgeted: float | None
    last_month_actual: float
    last_month_budgeted: float | None
    trailing_average_actual: float | None
    average_variance_pct: float | None
    month_actual: float


@dataclass(frozen=True)
class BudgetGridRow:
    type: str
    category: str
    # 12 entries, July through June (matching the Budget tab's Full year
    # column order) - None where that month has no Category Budget set
    # (unset != $0, CONTEXT.md's Category Budget entry).
    amounts: list[float | None]


@dataclass(frozen=True)
class DebtByNotes:
    notes: str
    amount: float
    pct_of_debt: float


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
    debt_summary: list[DebtByNotes]
    top_expenses: list[TopExpense]
    expenses_over_time: ExpensesOverTime


@dataclass(frozen=True)
class MonthlyTotals:
    year: int
    month: int
    income: float
    expenses: float
    debt: float
    net_balance: float
    saved: float


@dataclass(frozen=True)
class AnnualOverview:
    year: int
    elapsed_months: int
    stat_tiles: StatTiles
    monthly_average: StatTiles
    income_allocation: IncomeAllocation
    spending_by_category: list[CategorySpend]
    budgeted_vs_actual: list[BudgetVsActual]
    debt_summary: list[DebtByNotes]
    top_expenses: list[TopExpense]
    month_by_month: list[MonthlyTotals]
    income_vs_expenses_by_month: list[MonthlyTotals]


def get_month_overview(store, year: int, month: int) -> MonthOverview:
    transactions = [t for t in store.read_transactions() if t.date.year == year and t.date.month == month]
    stat_tiles = _stat_tiles(transactions)

    return MonthOverview(
        year=year,
        month=month,
        stat_tiles=stat_tiles,
        income_allocation=_income_allocation(
            stat_tiles.income, stat_tiles.expenses, stat_tiles.debt, stat_tiles.saved
        ),
        spending_by_category=_spending_by_category(transactions, stat_tiles.expenses),
        budgeted_vs_actual=_budgeted_vs_actual(
            transactions, store.read_category_budgets(year, month), store.read_categories()
        ),
        debt_summary=_debt_summary(transactions, stat_tiles.debt),
        top_expenses=_top_expenses(transactions, limit=5),
        expenses_over_time=_expenses_over_time(transactions, year, month),
    )


def get_annual_overview(store, year: int, today: date | None = None, start_month: int = 7) -> AnnualOverview:
    """The Full year Overview view-model for the year-shaped period starting
    `year`-`start_month` (7 for Financial Year, 1 for Calendar Year - see
    ADR-0021) - aggregated over elapsed months only (including the current
    in-progress month before it ends), never all twelve. See ADR-0011.
    """
    today = today if today is not None else date.today()
    elapsed_months = _elapsed_months(year, today, start_month)
    start = date(year, start_month, 1)
    end = _add_months(start, elapsed_months)
    transactions = [t for t in store.read_transactions() if start <= t.date < end]
    stat_tiles = _stat_tiles(transactions)
    monthly_totals = _monthly_totals(transactions, start)

    return AnnualOverview(
        year=year,
        elapsed_months=elapsed_months,
        stat_tiles=stat_tiles,
        monthly_average=_monthly_average(stat_tiles, elapsed_months),
        income_allocation=_income_allocation(
            stat_tiles.income, stat_tiles.expenses, stat_tiles.debt, stat_tiles.saved
        ),
        spending_by_category=_spending_by_category(transactions, stat_tiles.expenses),
        budgeted_vs_actual=_annual_budgeted_vs_actual(store, transactions, start, elapsed_months),
        debt_summary=_debt_summary(transactions, stat_tiles.debt),
        top_expenses=_top_expenses(transactions, limit=10),
        # Two named series over the same rows, not two computations: the Month
        # by month table and the Income vs Expenses chart both need one row
        # per month, but are separate fields (rather than one field two
        # components share) because Issue #41 specifies them as the API's two
        # separate contracts, matching how /api/annual-overview and
        # /api/overview are kept separate contracts rather than a shared one
        # with optional fields (ADR-0011).
        month_by_month=monthly_totals,
        income_vs_expenses_by_month=monthly_totals,
    )


def _budgetable_type_category_pairs(categories: list[Category]):
    """Every (Type, Category) pair a Category Budget can apply to, in
    CONTEXT.md's Type order and alphabetical within it - shared by
    get_budget_editor and get_full_year_budget_grid so both walk the same
    rows in the same order. Sourced from the live `categories` table (Issue
    #90), not the hardcoded CATEGORIES_BY_TYPE dict, so a Category added
    through Category Management (#91) shows up here too.
    """
    by_type = categories_by_type(categories)
    for transaction_type in TYPE_ORDER:
        if transaction_type not in BUDGETABLE_TYPES:
            continue
        for category in sorted(by_type.get(transaction_type, set())):
            yield transaction_type, category


def get_budget_editor(store, year: int, month: int, trailing_months: int = 3) -> list[BudgetEditorRow]:
    """The Budget tab's per-month editor rows - every Income/Expense/Debt
    Category with its current month's Category Budget (None if unset)
    alongside grey historical context: last month's actual, last month's own
    Category Budget (None if it was unset - unset != $0), a trailing average
    actual, an average variance % (how far actual has tended to run from
    Budgeted) over `trailing_months`, and the selected (year, month)'s own
    actual so far (month_actual - Issue #135). See Issue #63.

    The two windowed columns come back None - not a misleadingly small
    average - for a Category with fewer than `trailing_months` prior
    calendar months of its own Transaction history (checked per-Category,
    not store-wide: a Category with no Transactions of its own yet is
    insufficient even if other Categories go back further); a Category with
    sufficient history but no Category Budget set in any of those months
    gets a None average variance %, since there is nothing to measure
    variance against.
    """
    if trailing_months not in TRAILING_WINDOWS:
        raise ValueError(f"trailing_months must be one of {TRAILING_WINDOWS}, got {trailing_months}")

    categories = store.read_categories()
    selected_start = date(year, month, 1)
    # window_months[0] is last month (the anchor shown on its own, unwindowed);
    # window_months[-1] is the oldest month the window reaches back to.
    window_months = [_add_months(selected_start, -offset) for offset in range(1, trailing_months + 1)]
    window_start = window_months[-1]

    transactions = store.read_transactions()
    earliest_month_by_category = _earliest_month_by_category(transactions)

    # selected_start is folded into the same per-month totals computation as
    # window_months (rather than a second, separately-filtered pass) so
    # month_actual reuses exactly the shape last_month_actual already relies
    # on for its own month.
    actuals_by_month = {
        month_start: _totals_by_category(
            [t for t in transactions if t.date.year == month_start.year and t.date.month == month_start.month],
            BUDGETABLE_TYPES,
        )
        for month_start in [*window_months, selected_start]
    }
    current_budgets = store.read_category_budgets(year, month)
    last_month = window_months[0]
    last_month_budgets = store.read_category_budgets(last_month.year, last_month.month)

    rows = []
    for transaction_type, category in _budgetable_type_category_pairs(categories):
        category_earliest = earliest_month_by_category.get(category)
        has_sufficient_history = category_earliest is not None and category_earliest <= window_start
        trailing_average_actual, average_variance_pct = _trailing_history(
            store, category, window_months, actuals_by_month, has_sufficient_history
        )
        rows.append(
            BudgetEditorRow(
                type=transaction_type,
                category=category,
                budgeted=current_budgets.get(category),
                last_month_actual=_round(actuals_by_month[last_month].get(category, 0.0)),
                last_month_budgeted=last_month_budgets.get(category),
                trailing_average_actual=trailing_average_actual,
                average_variance_pct=average_variance_pct,
                month_actual=_round(actuals_by_month[selected_start].get(category, 0.0)),
            )
        )
    return rows


def get_full_year_budget_grid(store, year: int, start_month: int = 7) -> list[BudgetGridRow]:
    """The Budget tab's Full year read-only grid rows (Issue #64) - every
    Income/Expense/Debt Category (grouped by Type, alphabetical within it -
    same ordering as get_budget_editor) against its Category Budget for each
    of the 12 months of the year-shaped period starting `year`-`start_month`
    (7 for Financial Year, 1 for Calendar Year - ADR-0021), in that order.
    Unlike get_annual_overview, this is never restricted to elapsed months
    only: a Category Budget can be set ahead for a month that hasn't
    happened yet, and this grid shows it.
    """
    start = date(year, start_month, 1)
    months = [_add_months(start, offset) for offset in range(12)]
    budgets_by_month = {
        (month_start.year, month_start.month): store.read_category_budgets(month_start.year, month_start.month)
        for month_start in months
    }

    rows = []
    for transaction_type, category in _budgetable_type_category_pairs(store.read_categories()):
        amounts = [budgets_by_month[(month_start.year, month_start.month)].get(category) for month_start in months]
        rows.append(BudgetGridRow(type=transaction_type, category=category, amounts=amounts))
    return rows


def get_financial_year_transactions(store, year: int, month: int) -> list[Transaction]:
    """Every Transaction in the Financial Year starting `year`-`month`, newest
    first - see ADR-0010. Unlike get_month_overview, this hands back raw rows
    rather than an aggregate: the Transactions tab filters/searches/sorts them
    client-side, not this module.
    """
    start = date(year, month, 1)
    end = date(year + 1, month, 1)
    transactions = [t for t in store.read_transactions() if start <= t.date < end]
    return _newest_first(transactions)


def get_transactions_in_range(store, start: date, end: date) -> list[Transaction]:
    """Every Transaction between `start` and `end`, both bounds inclusive,
    newest first - the Export panel's query (Issue #96). Unlike
    get_financial_year_transactions, the range is caller-chosen rather than a
    Financial Year, so Export can span a Financial Year boundary.

    Filters/sorts server-side, same as get_financial_year_transactions -
    ADR-0010's "client-side filtering" choice was about the Transactions
    tab's own interactive filters, not about this query: a downloadable CSV
    has no client to filter in, so the range narrowing has to happen here.
    """
    transactions = [t for t in store.read_transactions() if start <= t.date <= end]
    return _newest_first(transactions)


def _newest_first(transactions: list[Transaction]) -> list[Transaction]:
    return sorted(transactions, key=lambda t: (t.date, t.id), reverse=True)


def get_latest_transaction_date(store) -> date | None:
    """The most recent date in the Transaction Log, or None if it is empty.

    Deliberately database-wide rather than per-month: this dates the data
    itself - how current the Transaction Log is - so it must not move when the
    reader switches months.
    """
    dates = [transaction.date for transaction in store.read_transactions()]
    return max(dates) if dates else None


def get_transaction_date_range(store) -> tuple[date | None, date | None]:
    """The earliest and latest dates in the Transaction Log, or (None, None)
    if it is empty - bounds which years the Financial Year switcher offers
    (ADR-0021).
    """
    dates = [transaction.date for transaction in store.read_transactions()]
    if not dates:
        return None, None
    return min(dates), max(dates)


def _stat_tiles(transactions: list[Transaction]) -> StatTiles:
    income = _round(sum(t.amount for t in transactions if t.type == "Income"))
    expenses = _round(sum(t.amount for t in transactions if t.type == "Expense"))
    debt = _round(sum(t.amount for t in transactions if t.type == "Debt"))
    saved = _round(sum(t.amount for t in transactions if t.type == "Savings"))
    net_balance = _round(income - expenses - debt)
    return StatTiles(income=income, expenses=expenses, debt=debt, net_balance=net_balance, saved=saved)


def _elapsed_months(year: int, today: date, start_month: int = 7) -> int:
    """How many months of the year-shaped period starting `year`-`start_month`
    have elapsed as of `today`, counting the current in-progress month - see
    ADR-0011. 0 before the period starts, 12 once it has fully finished.
    `start_month` is 7 for a Financial Year, 1 for a Calendar Year (ADR-0021).
    """
    start = date(year, start_month, 1)
    if today < start:
        return 0
    return min((today.year - start.year) * 12 + (today.month - start.month) + 1, 12)


def _add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    return date(start.year + month_index // 12, month_index % 12 + 1, 1)


def _monthly_average(totals: StatTiles, elapsed_months: int) -> StatTiles:
    if elapsed_months == 0:
        return StatTiles(income=0.0, expenses=0.0, debt=0.0, net_balance=0.0, saved=0.0)
    return StatTiles(
        income=_round(totals.income / elapsed_months),
        expenses=_round(totals.expenses / elapsed_months),
        debt=_round(totals.debt / elapsed_months),
        net_balance=_round(totals.net_balance / elapsed_months),
        saved=_round(totals.saved / elapsed_months),
    )


def _income_allocation(income: float, expenses: float, debt: float, saved: float) -> IncomeAllocation:
    if income <= 0:
        return IncomeAllocation(
            expenses_amount=expenses,
            expenses_pct=0.0,
            debt_amount=debt,
            debt_pct=0.0,
            saved_amount=saved,
            saved_pct=0.0,
            remaining_amount=0.0,
            remaining_pct=0.0,
            over_income_amount=0.0,
            over_income_pct=0.0,
        )

    remaining = income - expenses - debt - saved
    remaining_amount = max(remaining, 0.0)
    over_income_amount = max(-remaining, 0.0)

    return IncomeAllocation(
        expenses_amount=expenses,
        expenses_pct=_pct(expenses, income),
        debt_amount=debt,
        debt_pct=_pct(debt, income),
        saved_amount=saved,
        saved_pct=_pct(saved, income),
        remaining_amount=_round(remaining_amount),
        remaining_pct=_pct(remaining_amount, income),
        over_income_amount=_round(over_income_amount),
        over_income_pct=_pct(over_income_amount, income),
    )


def _totals_by_category(transactions: list[Transaction], types: set[str]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for t in transactions:
        if t.type not in types:
            continue
        totals[t.category] = totals.get(t.category, 0.0) + t.amount
    return totals


def _expense_totals_by_category(transactions: list[Transaction]) -> dict[str, float]:
    return _totals_by_category(transactions, {"Expense"})


def _spending_by_category(transactions: list[Transaction], expenses: float) -> list[CategorySpend]:
    totals = _expense_totals_by_category(transactions)

    rows = [
        CategorySpend(category=category, amount=_round(amount), pct_of_expenses=_pct(amount, expenses))
        for category, amount in totals.items()
        if amount != 0
    ]
    return sorted(rows, key=lambda row: (-row.amount, row.category))


def _debt_totals_by_notes(transactions: list[Transaction]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for t in transactions:
        if t.type != "Debt":
            continue
        totals[t.notes] = totals.get(t.notes, 0.0) + t.amount
    return totals


def _debt_summary(transactions: list[Transaction], debt: float) -> list[DebtByNotes]:
    """One row per distinct Notes among Debt Transactions, summed by Amount -
    shared by the per-month and Full year Overviews (Issues #51/#52), so their
    totals always match `stat_tiles.debt` rather than being computed
    independently.
    """
    totals = _debt_totals_by_notes(transactions)

    rows = [
        DebtByNotes(notes=notes, amount=_round(amount), pct_of_debt=_pct(amount, debt))
        for notes, amount in totals.items()
        if amount != 0
    ]
    return sorted(rows, key=lambda row: (-row.amount, row.notes))


def _budgeted_vs_actual_rows(
    budgets: dict[str, float], actuals: dict[str, float], categories: list[Category]
) -> list[BudgetVsActual]:
    """Build one row per Category with a budget and/or non-zero actual, sorted
    by Type (CONTEXT.md order) then Category - shared by the per-month and
    Full year Budgeted vs Actual tables, which differ only in how `budgets`
    and `actuals` are computed. Types are resolved from the live `categories`
    table (Issue #90), not the hardcoded CATEGORIES_BY_TYPE dict, so a
    Category added through Category Management (#91) isn't silently dropped.
    """
    type_by_category = type_lookup(categories)
    category_names = set(budgets) | {c for c, amount in actuals.items() if amount != 0}

    rows = []
    for category in category_names:
        transaction_type = type_by_category.get(category)
        if transaction_type is None:
            # A Category Budget can outlive its Category - e.g. Refund's
            # retirement (ADR-0016) left stale $0 rows behind from before
            # then. There's no Type section left to display it under, so
            # skip it rather than crash the sort below.
            continue
        budgeted = budgets.get(category)
        actual = _round(actuals.get(category, 0.0))
        # Positive diff = under budget (budget remaining); negative = overspent.
        diff = _round(budgeted - actual) if budgeted is not None else None
        pct = _pct(actual, budgeted) if budgeted is not None else None
        rows.append(
            BudgetVsActual(
                type=transaction_type, category=category, budgeted=budgeted, actual=actual, diff=diff, pct=pct
            )
        )

    return sorted(rows, key=lambda row: (TYPE_ORDER.index(row.type), row.category))


def _budgeted_vs_actual(
    transactions: list[Transaction], category_budgets: dict[str, float], categories: list[Category]
) -> list[BudgetVsActual]:
    actuals = _totals_by_category(transactions, BUDGETABLE_TYPES)
    return _budgeted_vs_actual_rows(category_budgets, actuals, categories)


def _summed_category_budgets(store, start: date, elapsed_months: int) -> dict[str, float]:
    """Each Category's Budgeted total across the Financial Year's elapsed
    months - a month with no Category Budget set contributes $0 to the sum
    (ADR-0013), so a Category only appears here at all if at least one elapsed
    month had one set.
    """
    sums: dict[str, float] = {}
    for offset in range(elapsed_months):
        month_start = _add_months(start, offset)
        for category, amount in store.read_category_budgets(month_start.year, month_start.month).items():
            sums[category] = sums.get(category, 0.0) + amount
    return sums


def _annual_budgeted_vs_actual(store, transactions: list[Transaction], start: date, elapsed_months: int) -> list[BudgetVsActual]:
    """Full year's Budgeted vs Actual rows - Budgeted is the real sum of each
    Category's per-month budgets across the elapsed Financial Year (ADR-0013),
    replacing ADR-0011's always-"—" placeholder.
    """
    budgets = _summed_category_budgets(store, start, elapsed_months)
    actuals = _totals_by_category(transactions, BUDGETABLE_TYPES)
    return _budgeted_vs_actual_rows(budgets, actuals, store.read_categories())


def _earliest_month_by_category(transactions: list[Transaction]) -> dict[str, date]:
    """Each Category's own earliest Transaction month - used to decide, per
    Category, whether a trailing window reaches back further than that
    Category's history goes (get_budget_editor).
    """
    earliest: dict[str, date] = {}
    for t in transactions:
        if t.type not in BUDGETABLE_TYPES:
            continue
        month_start = date(t.date.year, t.date.month, 1)
        if t.category not in earliest or month_start < earliest[t.category]:
            earliest[t.category] = month_start
    return earliest


def _trailing_history(
    store,
    category: str,
    window_months: list[date],
    actuals_by_month: dict[date, dict[str, float]],
    has_sufficient_history: bool,
) -> tuple[float | None, float | None]:
    """One Category's trailing average actual and average variance % across
    `window_months` - both None when that Category lacks enough history of
    its own for the window (get_budget_editor decides that per-Category), and
    the variance is also None on its own when none of those months had a
    Category Budget set to measure variance against.
    """
    if not has_sufficient_history:
        return None, None

    trailing_actuals = [actuals_by_month[month_start].get(category, 0.0) for month_start in window_months]
    trailing_average_actual = _round(sum(trailing_actuals) / len(window_months))

    window_end, window_start = window_months[0], window_months[-1]
    budgeted_by_month = store.read_category_budgets_for_range(
        category, window_start.year, window_start.month, window_end.year, window_end.month
    )
    variances = [
        _pct(actuals_by_month[month_start].get(category, 0.0), budgeted_by_month[(month_start.year, month_start.month)]) - 100
        for month_start in window_months
        if (month_start.year, month_start.month) in budgeted_by_month
    ]
    average_variance_pct = _round(sum(variances) / len(variances), digits=1) if variances else None

    return trailing_average_actual, average_variance_pct


def _monthly_totals(transactions: list[Transaction], start: date) -> list[MonthlyTotals]:
    """One row per month of the Financial Year starting `start`, in order -
    always 12, even for months past `transactions`' range (get_annual_overview
    only ever passes elapsed months in, so anything later naturally comes back
    zeroed rather than omitted - see Issue #41).
    """
    by_month: dict[tuple[int, int], list[Transaction]] = {}
    for t in transactions:
        by_month.setdefault((t.date.year, t.date.month), []).append(t)

    rows = []
    for offset in range(12):
        month_start = _add_months(start, offset)
        tiles = _stat_tiles(by_month.get((month_start.year, month_start.month), []))
        rows.append(
            MonthlyTotals(
                year=month_start.year,
                month=month_start.month,
                income=tiles.income,
                expenses=tiles.expenses,
                debt=tiles.debt,
                net_balance=tiles.net_balance,
                saved=tiles.saved,
            )
        )
    return rows


def _top_expenses(transactions: list[Transaction], limit: int) -> list[TopExpense]:
    expenses = [t for t in transactions if t.type == "Expense"]
    ranked = sorted(expenses, key=lambda t: (-t.amount, t.date, t.notes))
    return [
        TopExpense(notes=t.notes, category=t.category, date=t.date.isoformat(), amount=_round(t.amount))
        for t in ranked[:limit]
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
