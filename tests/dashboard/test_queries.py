import sqlite3
from datetime import date
from pathlib import Path

from dashboard.queries import (
    CategorySpend,
    get_annual_overview,
    get_financial_year_transactions,
    get_latest_transaction_date,
    get_month_overview,
)
from database.store import connect


def test_a_month_with_no_transactions_returns_a_zeroed_result(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.year == 2026
    assert overview.month == 8
    assert overview.stat_tiles.income == 0
    assert overview.stat_tiles.expenses == 0
    assert overview.stat_tiles.net_balance == 0
    assert overview.stat_tiles.transferred == 0
    assert overview.spending_by_category == []
    assert overview.budgeted_vs_actual == []
    assert overview.top_expenses == []
    assert overview.expenses_over_time.total == 0
    assert overview.expenses_over_time.daily_average == 0
    assert len(overview.expenses_over_time.daily) == 31  # every day of August


def test_stat_tiles_sum_by_type_for_the_selected_month(tmp_path: Path, make_candidate):
    database_path = tmp_path / "budget.db"
    store = connect(database_path)
    store.append_rows(
        [
            make_candidate(date=date(2026, 8, 1), amount=4000.0, type="Income", category="Salary", notes="Employer"),
            make_candidate(date=date(2026, 8, 2), amount=100.0, type="Income", category="Refund", notes="Return"),
            make_candidate(date=date(2026, 8, 3), amount=200.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_candidate(date=date(2026, 8, 4), amount=50.0, type="Expense", category="Transport", notes="Fuel"),
        ]
    )
    _insert_transaction(database_path, date="2026-08-05", amount=500.0, type="Transfer", category="Savings", notes="To savings")

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.stat_tiles.income == 4100.0
    assert overview.stat_tiles.expenses == 250.0
    assert overview.stat_tiles.transferred == 500.0


def test_net_balance_excludes_transfers(tmp_path: Path, make_candidate):
    database_path = tmp_path / "budget.db"
    store = connect(database_path)
    store.append_rows(
        [
            make_candidate(date=date(2026, 8, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_candidate(date=date(2026, 8, 2), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
        ]
    )
    _insert_transaction(database_path, date="2026-08-03", amount=5000.0, type="Transfer", category="Savings", notes="To savings")

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.stat_tiles.net_balance == 700.0


def test_transactions_outside_the_selected_month_are_excluded(tmp_path: Path, make_candidate):
    store = connect(tmp_path / "budget.db")
    store.append_rows(
        [
            make_candidate(date=date(2026, 7, 31), amount=100.0, type="Expense", category="Groceries", notes="Late July"),
            make_candidate(date=date(2026, 9, 1), amount=100.0, type="Expense", category="Groceries", notes="Early Sept"),
            make_candidate(date=date(2025, 8, 15), amount=100.0, type="Expense", category="Groceries", notes="Last year"),
            make_candidate(date=date(2026, 8, 15), amount=42.0, type="Expense", category="Groceries", notes="In month"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.stat_tiles.expenses == 42.0


def test_income_allocation_splits_expenses_transferred_and_remaining_as_pct_of_income(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 8, 2), amount=400.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 3), amount=100.0, type="Transfer", category="Savings", notes="To savings"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)
    allocation = overview.income_allocation

    assert allocation.expenses_amount == 400.0
    assert allocation.expenses_pct == 40.0
    assert allocation.transferred_amount == 100.0
    assert allocation.transferred_pct == 10.0
    assert allocation.remaining_amount == 500.0
    assert allocation.remaining_pct == 50.0
    assert allocation.over_income_amount == 0.0
    assert allocation.over_income_pct == 0.0


def test_income_allocation_reports_over_income_excess_when_outflows_exceed_income(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 8, 2), amount=900.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 3), amount=300.0, type="Transfer", category="Savings", notes="To savings"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)
    allocation = overview.income_allocation

    assert allocation.remaining_amount == 0.0
    assert allocation.remaining_pct == 0.0
    assert allocation.over_income_amount == 200.0
    assert allocation.over_income_pct == 20.0


def test_income_allocation_with_zero_income_reports_zero_pct_rather_than_dividing_by_zero(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=100.0, type="Expense", category="Groceries", notes="Woolworths"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)
    allocation = overview.income_allocation

    assert allocation.expenses_pct == 0.0
    assert allocation.transferred_pct == 0.0
    assert allocation.remaining_pct == 0.0
    assert allocation.over_income_pct == 0.0


def test_spending_by_category_only_includes_expense_categories_with_nonzero_spend(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 2), amount=100.0, type="Expense", category="Groceries", notes="Coles"),
            make_transaction(date=date(2026, 8, 3), amount=100.0, type="Expense", category="Transport", notes="Fuel"),
            make_transaction(date=date(2026, 8, 4), amount=1000.0, type="Income", category="Salary", notes="Employer"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.spending_by_category == [
        CategorySpend(category="Groceries", amount=400.0, pct_of_expenses=80.0),
        CategorySpend(category="Transport", amount=100.0, pct_of_expenses=20.0),
    ]


def test_budgeted_vs_actual_includes_budgeted_and_actual_categories_with_diff_and_pct(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=450.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 2), amount=80.0, type="Expense", category="Transport", notes="Fuel"),
        ],
        category_budgets={"Groceries": 500.0, "Entertainment & Leisure": 100.0},
    )

    overview = get_month_overview(store, year=2026, month=8)
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    # Diff = Expected - Actual: positive means under budget (budget remaining).
    assert by_category["Groceries"].expected == 500.0
    assert by_category["Groceries"].actual == 450.0
    assert by_category["Groceries"].diff == 50.0
    assert by_category["Groceries"].pct == 90.0

    assert by_category["Transport"].expected is None
    assert by_category["Transport"].actual == 80.0
    assert by_category["Transport"].diff is None
    assert by_category["Transport"].pct is None

    assert by_category["Entertainment & Leisure"].expected == 100.0
    assert by_category["Entertainment & Leisure"].actual == 0.0
    assert by_category["Entertainment & Leisure"].diff == 100.0
    assert by_category["Entertainment & Leisure"].pct == 0.0


def test_budgeted_vs_actual_excludes_categories_with_no_budget_and_no_spend(fake_store, make_transaction):
    store = fake_store(
        transactions=[make_transaction(date=date(2026, 8, 1), amount=450.0, type="Expense", category="Groceries", notes="Woolworths")],
        category_budgets={"Groceries": 500.0},
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert "Transport" not in {row.category for row in overview.budgeted_vs_actual}


def test_top_5_expenses_are_the_five_largest_that_month_descending(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=10.0, type="Expense", category="Groceries", notes="A"),
            make_transaction(date=date(2026, 8, 2), amount=90.0, type="Expense", category="Groceries", notes="B"),
            make_transaction(date=date(2026, 8, 3), amount=50.0, type="Expense", category="Groceries", notes="C"),
            make_transaction(date=date(2026, 8, 4), amount=70.0, type="Expense", category="Groceries", notes="D"),
            make_transaction(date=date(2026, 8, 5), amount=60.0, type="Expense", category="Groceries", notes="E"),
            make_transaction(date=date(2026, 8, 6), amount=40.0, type="Expense", category="Groceries", notes="F"),
            make_transaction(date=date(2026, 8, 7), amount=1000.0, type="Income", category="Salary", notes="Employer"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert [row.amount for row in overview.top_expenses] == [90.0, 70.0, 60.0, 50.0, 40.0]
    assert [row.notes for row in overview.top_expenses] == ["B", "D", "E", "C", "F"]


def test_top_5_expenses_tiebreaks_by_date_then_notes(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 5), amount=50.0, type="Expense", category="Groceries", notes="Zebra"),
            make_transaction(date=date(2026, 8, 1), amount=50.0, type="Expense", category="Groceries", notes="Apple"),
            make_transaction(date=date(2026, 8, 1), amount=50.0, type="Expense", category="Groceries", notes="Banana"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert [row.notes for row in overview.top_expenses] == ["Apple", "Banana", "Zebra"]


def test_expenses_over_time_is_a_cumulative_daily_total_for_every_day_of_the_month(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=100.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 3), amount=50.0, type="Expense", category="Transport", notes="Fuel"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)
    daily = overview.expenses_over_time.daily

    assert len(daily) == 31
    assert daily[0].date == "2026-08-01"
    assert daily[0].cumulative == 100.0
    assert daily[1].cumulative == 100.0  # no transaction on day 2 - carries forward
    assert daily[2].cumulative == 150.0
    assert daily[-1].cumulative == 150.0
    assert overview.expenses_over_time.total == 150.0
    assert overview.expenses_over_time.daily_average == round(150.0 / 31, 2)


def test_annual_overview_before_the_financial_year_starts_elapses_no_months(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    overview = get_annual_overview(store, year=2026, today=date(2026, 6, 15))

    assert overview.year == 2026
    assert overview.elapsed_months == 0
    assert overview.stat_tiles.income == 0
    assert overview.monthly_average.income == 0


def test_annual_overview_counts_the_current_in_progress_month_as_elapsed(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 10), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 8, 5), amount=500.0, type="Income", category="Salary", notes="Employer"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert overview.elapsed_months == 2
    assert overview.stat_tiles.income == 1500.0


def test_annual_overview_excludes_transactions_from_months_not_yet_elapsed(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 5), amount=500.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 9, 1), amount=999.0, type="Expense", category="Groceries", notes="Not yet elapsed"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert overview.stat_tiles.expenses == 500.0


def test_annual_overview_excludes_transactions_from_before_the_financial_year(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 6, 30), amount=500.0, type="Expense", category="Groceries", notes="Last FY"),
            make_transaction(date=date(2026, 7, 1), amount=250.0, type="Expense", category="Groceries", notes="This FY"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert overview.stat_tiles.expenses == 250.0


def test_annual_overview_monthly_average_divides_totals_by_elapsed_months_not_twelve(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 5), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 8, 5), amount=1000.0, type="Income", category="Salary", notes="Employer"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert overview.elapsed_months == 2
    assert overview.stat_tiles.income == 2000.0
    assert overview.monthly_average.income == 1000.0


def test_annual_overview_on_a_completed_financial_year_elapses_all_twelve_months(fake_store):
    store = fake_store(transactions=[])

    overview = get_annual_overview(store, year=2026, today=date(2027, 8, 1))

    assert overview.elapsed_months == 12


def test_annual_overview_income_allocation_is_computed_over_elapsed_months(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 7, 2), amount=400.0, type="Expense", category="Groceries", notes="Woolworths"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 7, 15))

    assert overview.income_allocation.expenses_amount == 400.0
    assert overview.income_allocation.expenses_pct == 40.0


def test_annual_overview_spending_by_category_sums_actual_expenses_over_elapsed_months(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 1), amount=100.0, type="Expense", category="Groceries", notes="Coles"),
            make_transaction(date=date(2026, 8, 2), amount=100.0, type="Expense", category="Transport", notes="Fuel"),
            make_transaction(date=date(2026, 9, 1), amount=999.0, type="Expense", category="Groceries", notes="Not yet elapsed"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert overview.spending_by_category == [
        CategorySpend(category="Groceries", amount=400.0, pct_of_expenses=80.0),
        CategorySpend(category="Transport", amount=100.0, pct_of_expenses=20.0),
    ]


def test_annual_overview_budgeted_vs_actual_expected_is_always_null_regardless_of_category_budget(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=450.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 7, 2), amount=80.0, type="Expense", category="Transport", notes="Fuel"),
        ],
        category_budgets={"Groceries": 500.0, "Entertainment & Leisure": 100.0},
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 7, 15))
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Groceries"].expected is None
    assert by_category["Groceries"].actual == 450.0
    assert by_category["Groceries"].diff is None
    assert by_category["Groceries"].pct is None

    assert by_category["Transport"].expected is None
    assert by_category["Transport"].actual == 80.0

    # A Category Budget with no spend this Financial Year doesn't get a row -
    # real annual budgeting is deferred (ADR-0011), so only actual spend
    # determines the row set, unlike the per-month table.
    assert "Entertainment & Leisure" not in by_category


def _insert_transaction(database_path: Path, **fields) -> None:
    connection = sqlite3.connect(database_path)
    connection.execute(
        "INSERT INTO transactions (date, amount, type, category, notes) "
        "VALUES (:date, :amount, :type, :category, :notes)",
        fields,
    )
    connection.commit()
    connection.close()


def test_latest_transaction_date_on_an_empty_log_is_none(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    assert get_latest_transaction_date(store) is None


def test_latest_transaction_date_is_the_most_recent_transaction(tmp_path: Path, make_candidate):
    store = connect(tmp_path / "budget.db")
    store.append_rows(
        [
            make_candidate(date=date(2026, 6, 30)),
            make_candidate(date=date(2026, 8, 3)),
            make_candidate(date=date(2026, 7, 15)),
        ]
    )

    assert get_latest_transaction_date(store) == date(2026, 8, 3)


def test_financial_year_transactions_on_an_empty_database_returns_no_transactions(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    assert get_financial_year_transactions(store, year=2026, month=7) == []


def test_financial_year_transactions_spans_both_calendar_years_it_covers(tmp_path: Path, make_candidate):
    store = connect(tmp_path / "budget.db")
    store.append_rows(
        [
            make_candidate(date=date(2026, 6, 30), notes="Last day of FY25-26"),
            make_candidate(date=date(2026, 7, 1), notes="First day of FY26-27"),
            make_candidate(date=date(2027, 6, 30), notes="Last day of FY26-27"),
            make_candidate(date=date(2027, 7, 1), notes="First day of FY27-28"),
        ]
    )

    notes = {t.notes for t in get_financial_year_transactions(store, year=2026, month=7)}

    assert notes == {"First day of FY26-27", "Last day of FY26-27"}


def test_financial_year_transactions_are_sorted_newest_first(tmp_path: Path, make_candidate):
    store = connect(tmp_path / "budget.db")
    store.append_rows(
        [
            make_candidate(date=date(2026, 8, 1), notes="Oldest"),
            make_candidate(date=date(2027, 3, 1), notes="Newest"),
            make_candidate(date=date(2026, 12, 1), notes="Middle"),
        ]
    )

    ordered = get_financial_year_transactions(store, year=2026, month=7)

    assert [t.notes for t in ordered] == ["Newest", "Middle", "Oldest"]


def test_financial_year_transactions_include_their_id(tmp_path: Path, make_candidate):
    store = connect(tmp_path / "budget.db")
    store.append_rows([make_candidate(date=date(2026, 8, 1))])

    [transaction] = get_financial_year_transactions(store, year=2026, month=7)

    assert transaction.id is not None


def test_latest_transaction_date_counts_every_type_not_just_expenses(tmp_path: Path, make_candidate):
    # The "As at" line says how current the Transaction Log is, so a Transfer
    # or an Income row dates it just as well as an Expense does.
    store = connect(tmp_path / "budget.db")
    store.append_rows(
        [
            make_candidate(date=date(2026, 7, 1), type="Expense", category="Groceries"),
            make_candidate(date=date(2026, 8, 3), type="Income", category="Salary"),
        ]
    )

    assert get_latest_transaction_date(store) == date(2026, 8, 3)
