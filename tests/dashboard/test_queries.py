import sqlite3
from datetime import date
from pathlib import Path

import pytest

from dashboard.queries import (
    CategorySpend,
    DebtByNotes,
    MonthlyTotals,
    get_annual_overview,
    get_budget_editor,
    get_financial_year_transactions,
    get_full_year_budget_grid,
    get_latest_transaction_date,
    get_month_overview,
    get_transaction_date_range,
    get_transactions_in_range,
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
    assert overview.debt_summary == []
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
            make_candidate(date=date(2026, 8, 2), amount=100.0, type="Income", category="Rental", notes="Tenant"),
            make_candidate(date=date(2026, 8, 3), amount=200.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_candidate(date=date(2026, 8, 4), amount=50.0, type="Expense", category="Transport", notes="Fuel"),
            make_candidate(date=date(2026, 8, 5), amount=875.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ]
    )
    _insert_transaction(database_path, date="2026-08-06", amount=500.0, type="Transfer", category="Savings", notes="To savings")

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.stat_tiles.income == 4100.0
    assert overview.stat_tiles.expenses == 250.0
    assert overview.stat_tiles.debt == 875.0
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


def test_net_balance_subtracts_debt(tmp_path: Path, make_candidate):
    database_path = tmp_path / "budget.db"
    store = connect(database_path)
    store.append_rows(
        [
            make_candidate(date=date(2026, 8, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_candidate(date=date(2026, 8, 2), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_candidate(date=date(2026, 8, 3), amount=200.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.stat_tiles.net_balance == 500.0


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


def test_income_allocation_includes_a_debt_share_of_income(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 8, 2), amount=400.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 3), amount=200.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 8, 4), amount=100.0, type="Transfer", category="Savings", notes="To savings"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)
    allocation = overview.income_allocation

    assert allocation.debt_amount == 200.0
    assert allocation.debt_pct == 20.0
    assert allocation.remaining_amount == 300.0
    assert allocation.remaining_pct == 30.0


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


def test_spending_by_category_excludes_debt(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 2), amount=875.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.spending_by_category == [
        CategorySpend(category="Groceries", amount=300.0, pct_of_expenses=100.0),
    ]


def test_debt_summary_groups_by_notes_summed_and_sorted_descending(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=800.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 8, 15), amount=800.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 8, 5), amount=500.0, type="Debt", category="Mortgage Repayment", notes="Investment property"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.debt_summary == [
        DebtByNotes(notes="Werribee", amount=1600.0, pct_of_debt=76.2),
        DebtByNotes(notes="Investment property", amount=500.0, pct_of_debt=23.8),
    ]


def test_debt_summary_breaks_ties_alphabetically_by_notes(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=500.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 8, 2), amount=500.0, type="Debt", category="Mortgage Repayment", notes="Ascot Vale"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert [row.notes for row in overview.debt_summary] == ["Ascot Vale", "Werribee"]


def test_debt_summary_total_matches_stat_tiles_debt(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=800.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 8, 2), amount=500.0, type="Debt", category="Mortgage Repayment", notes="Investment property"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert sum(row.amount for row in overview.debt_summary) == overview.stat_tiles.debt


def test_debt_summary_excludes_non_debt_types(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 2), amount=1000.0, type="Income", category="Salary", notes="Employer"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.debt_summary == []


def test_debt_summary_is_empty_for_a_month_with_no_debt_transactions(fake_store):
    store = fake_store(transactions=[])

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.debt_summary == []


def test_budgeted_vs_actual_includes_budgeted_and_actual_categories_with_diff_and_pct(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=450.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 2), amount=80.0, type="Expense", category="Transport", notes="Fuel"),
        ],
        category_budgets={("Groceries", 2026, 8): 500.0, ("Entertainment & Leisure", 2026, 8): 100.0},
    )

    overview = get_month_overview(store, year=2026, month=8)
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    # Diff = Budgeted - Actual: positive means under budget (budget remaining).
    assert by_category["Groceries"].type == "Expense"
    assert by_category["Groceries"].budgeted == 500.0
    assert by_category["Groceries"].actual == 450.0
    assert by_category["Groceries"].diff == 50.0
    assert by_category["Groceries"].pct == 90.0

    assert by_category["Transport"].budgeted is None
    assert by_category["Transport"].actual == 80.0
    assert by_category["Transport"].diff is None
    assert by_category["Transport"].pct is None

    assert by_category["Entertainment & Leisure"].budgeted == 100.0
    assert by_category["Entertainment & Leisure"].actual == 0.0
    assert by_category["Entertainment & Leisure"].diff == 100.0
    assert by_category["Entertainment & Leisure"].pct == 0.0


def test_budgeted_vs_actual_excludes_categories_with_no_budget_and_no_spend(fake_store, make_transaction):
    store = fake_store(
        transactions=[make_transaction(date=date(2026, 8, 1), amount=450.0, type="Expense", category="Groceries", notes="Woolworths")],
        category_budgets={("Groceries", 2026, 8): 500.0},
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert "Transport" not in {row.category for row in overview.budgeted_vs_actual}


def test_budgeted_vs_actual_skips_a_stale_budget_for_a_retired_category(fake_store, make_transaction):
    # ADR-0016 retired Refund as a Category. A Category Budget written for it
    # before retirement (e.g. via the Budget tab's Auto-populate) can still
    # exist in the store - type_for_category("Refund") now returns None, so
    # this stale row must be skipped rather than crashing the sort by Type.
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=450.0, type="Expense", category="Groceries", notes="Woolworths"),
        ],
        category_budgets={("Groceries", 2026, 8): 500.0, ("Refund", 2026, 8): 0.0},
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert "Refund" not in {row.category for row in overview.budgeted_vs_actual}
    assert {row.category for row in overview.budgeted_vs_actual} == {"Groceries"}


def test_budgeted_vs_actual_includes_a_category_added_through_category_management(fake_store, make_transaction):
    # Issue #90 - Type is resolved from the live `categories` table, not the
    # hardcoded CATEGORIES_BY_TYPE dict, so a Category added via Category
    # Management (#91) isn't silently dropped from spending it has.
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=45.0, type="Expense", category="Pet Care", notes="Vet"),
        ]
    )
    store.create_category("Expense", "Pet Care", None)

    overview = get_month_overview(store, year=2026, month=8)
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Pet Care"].type == "Expense"
    assert by_category["Pet Care"].actual == 45.0


def test_budgeted_vs_actual_includes_income_and_debt_categories(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=4200.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 8, 2), amount=900.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ],
        category_budgets={("Salary", 2026, 8): 4000.0, ("Mortgage Repayment", 2026, 8): 850.0},
    )

    overview = get_month_overview(store, year=2026, month=8)
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Salary"].type == "Income"
    assert by_category["Salary"].budgeted == 4000.0
    assert by_category["Salary"].actual == 4200.0
    assert by_category["Salary"].diff == -200.0

    assert by_category["Mortgage Repayment"].type == "Debt"
    assert by_category["Mortgage Repayment"].budgeted == 850.0
    assert by_category["Mortgage Repayment"].actual == 900.0
    assert by_category["Mortgage Repayment"].diff == -50.0


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


def test_top_5_expenses_excludes_debt(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=10.0, type="Expense", category="Groceries", notes="A"),
            make_transaction(date=date(2026, 8, 2), amount=875.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert [row.notes for row in overview.top_expenses] == ["A"]


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


def test_expenses_over_time_excludes_debt(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=100.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 3), amount=875.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.expenses_over_time.total == 100.0


def test_annual_overview_before_the_financial_year_starts_elapses_no_months(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    overview = get_annual_overview(store, year=2026, today=date(2026, 6, 15))

    assert overview.year == 2026
    assert overview.elapsed_months == 0
    assert overview.stat_tiles.income == 0
    assert overview.monthly_average.income == 0
    assert overview.top_expenses == []


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


def test_annual_overview_stat_tiles_and_monthly_average_include_debt(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=800.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 8, 1), amount=800.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert overview.stat_tiles.debt == 1600.0
    assert overview.monthly_average.debt == 800.0


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


def test_annual_overview_spending_by_category_excludes_debt(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 7, 2), amount=875.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 7, 15))

    assert overview.spending_by_category == [
        CategorySpend(category="Groceries", amount=300.0, pct_of_expenses=100.0),
    ]


def test_annual_overview_debt_summary_sums_by_notes_over_elapsed_months(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=800.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 8, 1), amount=800.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 9, 1), amount=999.0, type="Debt", category="Mortgage Repayment", notes="Not yet elapsed"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert overview.debt_summary == [
        DebtByNotes(notes="Werribee", amount=1600.0, pct_of_debt=100.0),
    ]


def test_annual_overview_debt_summary_total_matches_stat_tiles_debt(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=800.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 8, 1), amount=500.0, type="Debt", category="Mortgage Repayment", notes="Investment property"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert sum(row.amount for row in overview.debt_summary) == overview.stat_tiles.debt


def test_annual_overview_debt_summary_excludes_non_debt_types(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert overview.debt_summary == []


def test_annual_overview_debt_summary_is_empty_with_no_debt_transactions(fake_store):
    store = fake_store(transactions=[])

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert overview.debt_summary == []


def test_annual_overview_budgeted_vs_actual_sums_category_budgets_across_elapsed_months(fake_store, make_transaction):
    # Financial Year 2026 starting July; today=2026-09-10 puts July/Aug/Sept
    # elapsed (ADR-0011's "elapsed months" rule).
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=450.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 1), amount=500.0, type="Expense", category="Groceries", notes="Coles"),
            make_transaction(date=date(2026, 9, 1), amount=520.0, type="Expense", category="Groceries", notes="Aldi"),
        ],
        category_budgets={
            ("Groceries", 2026, 7): 500.0,
            ("Groceries", 2026, 8): 500.0,
            ("Groceries", 2026, 9): 500.0,
        },
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 9, 10))
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Groceries"].budgeted == 1500.0
    assert by_category["Groceries"].actual == 1470.0
    assert by_category["Groceries"].diff == 30.0


def test_annual_overview_budgeted_vs_actual_treats_a_month_with_no_budget_as_zero_not_unset(
    fake_store, make_transaction
):
    # Groceries is only budgeted for July and Sept, not Aug - the elapsed
    # months' Full year sum still comes back with a partial total (ADR-0013),
    # not unset for the whole Category.
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=450.0, type="Expense", category="Groceries", notes="Woolworths"),
        ],
        category_budgets={("Groceries", 2026, 7): 500.0, ("Groceries", 2026, 9): 500.0},
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 9, 10))
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Groceries"].budgeted == 1000.0


def test_annual_overview_budgeted_vs_actual_excludes_a_budget_set_for_a_future_month(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=450.0, type="Expense", category="Groceries", notes="Woolworths"),
        ],
        category_budgets={("Groceries", 2026, 7): 500.0, ("Groceries", 2026, 12): 999.0},
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 7, 15))
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Groceries"].budgeted == 500.0


def test_annual_overview_budgeted_vs_actual_is_unset_for_a_category_never_budgeted(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=80.0, type="Expense", category="Transport", notes="Fuel"),
        ],
        category_budgets={("Groceries", 2026, 7): 500.0},
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 7, 15))
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Transport"].budgeted is None
    assert by_category["Transport"].diff is None

    # A Category Budget with no spend this Financial Year still doesn't get a
    # row - only actual spend or a Budgeted total determines the row set.
    assert "Entertainment & Leisure" not in by_category


def test_annual_overview_budgeted_vs_actual_includes_income_and_debt_categories(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=4200.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 7, 2), amount=900.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ],
        category_budgets={("Salary", 2026, 7): 4000.0, ("Mortgage Repayment", 2026, 7): 850.0},
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 7, 15))
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Salary"].type == "Income"
    assert by_category["Salary"].budgeted == 4000.0
    assert by_category["Mortgage Repayment"].type == "Debt"
    assert by_category["Mortgage Repayment"].budgeted == 850.0


def test_annual_overview_top_expenses_are_the_ten_largest_across_elapsed_months(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, d), amount=amount, type="Expense", category="Groceries", notes=str(amount))
            for d, amount in enumerate([10.0, 90.0, 50.0, 70.0, 60.0, 40.0, 30.0, 20.0, 80.0, 100.0, 110.0], start=1)
        ]
        + [make_transaction(date=date(2026, 8, 1), amount=1000.0, type="Income", category="Salary", notes="Employer")]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert len(overview.top_expenses) == 10
    assert [row.amount for row in overview.top_expenses] == [110.0, 100.0, 90.0, 80.0, 70.0, 60.0, 50.0, 40.0, 30.0, 20.0]


def test_annual_overview_top_expenses_excludes_debt(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=10.0, type="Expense", category="Groceries", notes="A"),
            make_transaction(date=date(2026, 7, 2), amount=875.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 7, 15))

    assert [row.notes for row in overview.top_expenses] == ["A"]


def test_annual_overview_top_expenses_excludes_transactions_from_months_not_yet_elapsed(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 5), amount=500.0, type="Expense", category="Groceries", notes="Elapsed"),
            make_transaction(date=date(2026, 9, 1), amount=999.0, type="Expense", category="Groceries", notes="Not yet elapsed"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert [row.notes for row in overview.top_expenses] == ["Elapsed"]


def test_annual_overview_top_expenses_tiebreaks_by_date_then_notes(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 5), amount=50.0, type="Expense", category="Groceries", notes="Zebra"),
            make_transaction(date=date(2026, 7, 1), amount=50.0, type="Expense", category="Groceries", notes="Apple"),
            make_transaction(date=date(2026, 7, 1), amount=50.0, type="Expense", category="Groceries", notes="Banana"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 7, 15))

    assert [row.notes for row in overview.top_expenses] == ["Apple", "Banana", "Zebra"]


def test_annual_overview_month_by_month_always_has_twelve_entries_in_financial_year_order(fake_store):
    store = fake_store(transactions=[])

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert len(overview.month_by_month) == 12
    assert [(row.year, row.month) for row in overview.month_by_month] == [
        (2026, 7), (2026, 8), (2026, 9), (2026, 10), (2026, 11), (2026, 12),
        (2027, 1), (2027, 2), (2027, 3), (2027, 4), (2027, 5), (2027, 6),
    ]


def test_annual_overview_month_by_month_sums_each_month_independently(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 7, 2), amount=400.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 7, 2), amount=150.0, type="Debt", category="Mortgage Repayment", notes="Repayment"),
            make_transaction(date=date(2026, 7, 3), amount=100.0, type="Transfer", category="Savings", notes="To savings"),
            make_transaction(date=date(2026, 8, 5), amount=500.0, type="Income", category="Salary", notes="Employer"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))
    by_month = {(row.year, row.month): row for row in overview.month_by_month}

    july = by_month[(2026, 7)]
    assert july.income == 1000.0
    assert july.expenses == 400.0
    assert july.debt == 150.0
    assert july.net_balance == 450.0
    assert july.transferred == 100.0

    august = by_month[(2026, 8)]
    assert august.income == 500.0
    assert august.expenses == 0.0
    assert august.net_balance == 500.0
    assert august.transferred == 0.0


def test_annual_overview_month_by_month_zero_fills_months_not_yet_elapsed(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 9, 1), amount=999.0, type="Expense", category="Groceries", notes="Not yet elapsed"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))
    by_month = {(row.year, row.month): row for row in overview.month_by_month}

    # September hasn't elapsed as of 21 Aug, so it's a zeroed row, not omitted
    # or carrying September's not-yet-counted spend.
    assert by_month[(2026, 9)] == MonthlyTotals(
        year=2026, month=9, income=0.0, expenses=0.0, debt=0.0, net_balance=0.0, transferred=0.0
    )
    assert len(overview.month_by_month) == 12


def test_annual_overview_income_vs_expenses_by_month_matches_month_by_month(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert overview.income_vs_expenses_by_month == overview.month_by_month


def test_annual_overview_before_the_calendar_year_starts_elapses_no_months(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    overview = get_annual_overview(store, year=2026, today=date(2025, 12, 15), start_month=1)

    assert overview.year == 2026
    assert overview.elapsed_months == 0
    assert overview.stat_tiles.income == 0


def test_annual_overview_counts_the_current_in_progress_month_as_elapsed_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 10), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 2, 5), amount=500.0, type="Income", category="Salary", notes="Employer"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)

    assert overview.elapsed_months == 2
    assert overview.stat_tiles.income == 1500.0


def test_annual_overview_on_a_completed_calendar_year_elapses_all_twelve_months(fake_store):
    store = fake_store(transactions=[])

    overview = get_annual_overview(store, year=2026, today=date(2027, 2, 1), start_month=1)

    assert overview.elapsed_months == 12


def test_annual_overview_excludes_transactions_from_before_the_calendar_year(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2025, 12, 31), amount=500.0, type="Expense", category="Groceries", notes="Last CY"),
            make_transaction(date=date(2026, 1, 1), amount=250.0, type="Expense", category="Groceries", notes="This CY"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)

    assert overview.stat_tiles.expenses == 250.0


def test_annual_overview_budgeted_vs_actual_sums_category_budgets_across_elapsed_months_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=450.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 2, 1), amount=500.0, type="Expense", category="Groceries", notes="Coles"),
            make_transaction(date=date(2026, 3, 1), amount=520.0, type="Expense", category="Groceries", notes="Aldi"),
        ],
        category_budgets={
            ("Groceries", 2026, 1): 500.0,
            ("Groceries", 2026, 2): 500.0,
            ("Groceries", 2026, 3): 500.0,
        },
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 3, 10), start_month=1)
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Groceries"].budgeted == 1500.0
    assert by_category["Groceries"].actual == 1470.0
    assert by_category["Groceries"].diff == 30.0


def test_annual_overview_month_by_month_always_has_twelve_entries_in_calendar_year_order(fake_store):
    store = fake_store(transactions=[])

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21), start_month=1)

    assert len(overview.month_by_month) == 12
    assert [(row.year, row.month) for row in overview.month_by_month] == [
        (2026, 1), (2026, 2), (2026, 3), (2026, 4), (2026, 5), (2026, 6),
        (2026, 7), (2026, 8), (2026, 9), (2026, 10), (2026, 11), (2026, 12),
    ]


def test_annual_overview_month_by_month_zero_fills_months_not_yet_elapsed_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 3, 1), amount=999.0, type="Expense", category="Groceries", notes="Not yet elapsed"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)
    by_month = {(row.year, row.month): row for row in overview.month_by_month}

    assert by_month[(2026, 3)] == MonthlyTotals(
        year=2026, month=3, income=0.0, expenses=0.0, debt=0.0, net_balance=0.0, transferred=0.0
    )
    assert len(overview.month_by_month) == 12


def test_annual_overview_monthly_average_divides_totals_by_elapsed_months_not_twelve_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 5), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 2, 5), amount=1000.0, type="Income", category="Salary", notes="Employer"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)

    assert overview.elapsed_months == 2
    assert overview.stat_tiles.income == 2000.0
    assert overview.monthly_average.income == 1000.0


def test_annual_overview_stat_tiles_and_monthly_average_include_debt_for_calendar_year(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=800.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 2, 1), amount=800.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)

    assert overview.stat_tiles.debt == 1600.0
    assert overview.monthly_average.debt == 800.0


def test_annual_overview_income_allocation_is_computed_over_elapsed_months_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 1, 2), amount=400.0, type="Expense", category="Groceries", notes="Woolworths"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 1, 15), start_month=1)

    assert overview.income_allocation.expenses_amount == 400.0
    assert overview.income_allocation.expenses_pct == 40.0


def test_annual_overview_spending_by_category_sums_actual_expenses_over_elapsed_months_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 2, 1), amount=100.0, type="Expense", category="Groceries", notes="Coles"),
            make_transaction(date=date(2026, 2, 2), amount=100.0, type="Expense", category="Transport", notes="Fuel"),
            make_transaction(date=date(2026, 3, 1), amount=999.0, type="Expense", category="Groceries", notes="Not yet elapsed"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)

    assert overview.spending_by_category == [
        CategorySpend(category="Groceries", amount=400.0, pct_of_expenses=80.0),
        CategorySpend(category="Transport", amount=100.0, pct_of_expenses=20.0),
    ]


def test_annual_overview_spending_by_category_excludes_debt_for_calendar_year(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 1, 2), amount=875.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 1, 15), start_month=1)

    assert overview.spending_by_category == [
        CategorySpend(category="Groceries", amount=300.0, pct_of_expenses=100.0),
    ]


def test_annual_overview_debt_summary_sums_by_notes_over_elapsed_months_for_calendar_year(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=800.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 2, 1), amount=800.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 3, 1), amount=999.0, type="Debt", category="Mortgage Repayment", notes="Not yet elapsed"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)

    assert overview.debt_summary == [
        DebtByNotes(notes="Werribee", amount=1600.0, pct_of_debt=100.0),
    ]


def test_annual_overview_debt_summary_total_matches_stat_tiles_debt_for_calendar_year(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=800.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 2, 1), amount=500.0, type="Debt", category="Mortgage Repayment", notes="Investment property"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)

    assert sum(row.amount for row in overview.debt_summary) == overview.stat_tiles.debt


def test_annual_overview_debt_summary_excludes_non_debt_types_for_calendar_year(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)

    assert overview.debt_summary == []


def test_annual_overview_debt_summary_is_empty_with_no_debt_transactions_for_calendar_year(fake_store):
    store = fake_store(transactions=[])

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)

    assert overview.debt_summary == []


def test_annual_overview_budgeted_vs_actual_treats_a_month_with_no_budget_as_zero_not_unset_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=450.0, type="Expense", category="Groceries", notes="Woolworths"),
        ],
        category_budgets={("Groceries", 2026, 1): 500.0, ("Groceries", 2026, 3): 500.0},
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 3, 10), start_month=1)
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Groceries"].budgeted == 1000.0


def test_annual_overview_budgeted_vs_actual_excludes_a_budget_set_for_a_future_month_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=450.0, type="Expense", category="Groceries", notes="Woolworths"),
        ],
        category_budgets={("Groceries", 2026, 1): 500.0, ("Groceries", 2026, 12): 999.0},
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 1, 15), start_month=1)
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Groceries"].budgeted == 500.0


def test_annual_overview_budgeted_vs_actual_is_unset_for_a_category_never_budgeted_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=80.0, type="Expense", category="Transport", notes="Fuel"),
        ],
        category_budgets={("Groceries", 2026, 1): 500.0},
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 1, 15), start_month=1)
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Transport"].budgeted is None
    assert by_category["Transport"].diff is None
    assert "Entertainment & Leisure" not in by_category


def test_annual_overview_budgeted_vs_actual_includes_income_and_debt_categories_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=4200.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 1, 2), amount=900.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ],
        category_budgets={("Salary", 2026, 1): 4000.0, ("Mortgage Repayment", 2026, 1): 850.0},
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 1, 15), start_month=1)
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Salary"].type == "Income"
    assert by_category["Salary"].budgeted == 4000.0
    assert by_category["Mortgage Repayment"].type == "Debt"
    assert by_category["Mortgage Repayment"].budgeted == 850.0


def test_annual_overview_top_expenses_are_the_ten_largest_across_elapsed_months_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, d), amount=amount, type="Expense", category="Groceries", notes=str(amount))
            for d, amount in enumerate([10.0, 90.0, 50.0, 70.0, 60.0, 40.0, 30.0, 20.0, 80.0, 100.0, 110.0], start=1)
        ]
        + [make_transaction(date=date(2026, 2, 1), amount=1000.0, type="Income", category="Salary", notes="Employer")]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)

    assert len(overview.top_expenses) == 10
    assert [row.amount for row in overview.top_expenses] == [110.0, 100.0, 90.0, 80.0, 70.0, 60.0, 50.0, 40.0, 30.0, 20.0]


def test_annual_overview_top_expenses_excludes_debt_for_calendar_year(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=10.0, type="Expense", category="Groceries", notes="A"),
            make_transaction(date=date(2026, 1, 2), amount=875.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 1, 15), start_month=1)

    assert [row.notes for row in overview.top_expenses] == ["A"]


def test_annual_overview_top_expenses_excludes_transactions_from_months_not_yet_elapsed_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 2, 5), amount=500.0, type="Expense", category="Groceries", notes="Elapsed"),
            make_transaction(date=date(2026, 3, 1), amount=999.0, type="Expense", category="Groceries", notes="Not yet elapsed"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)

    assert [row.notes for row in overview.top_expenses] == ["Elapsed"]


def test_annual_overview_top_expenses_tiebreaks_by_date_then_notes_for_calendar_year(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 5), amount=50.0, type="Expense", category="Groceries", notes="Zebra"),
            make_transaction(date=date(2026, 1, 1), amount=50.0, type="Expense", category="Groceries", notes="Apple"),
            make_transaction(date=date(2026, 1, 1), amount=50.0, type="Expense", category="Groceries", notes="Banana"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 1, 15), start_month=1)

    assert [row.notes for row in overview.top_expenses] == ["Apple", "Banana", "Zebra"]


def test_annual_overview_month_by_month_sums_each_month_independently_for_calendar_year(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 1, 2), amount=400.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 1, 2), amount=150.0, type="Debt", category="Mortgage Repayment", notes="Repayment"),
            make_transaction(date=date(2026, 1, 3), amount=100.0, type="Transfer", category="Savings", notes="To savings"),
            make_transaction(date=date(2026, 2, 5), amount=500.0, type="Income", category="Salary", notes="Employer"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)
    by_month = {(row.year, row.month): row for row in overview.month_by_month}

    january = by_month[(2026, 1)]
    assert january.income == 1000.0
    assert january.expenses == 400.0
    assert january.debt == 150.0
    assert january.net_balance == 450.0
    assert january.transferred == 100.0

    february = by_month[(2026, 2)]
    assert february.income == 500.0
    assert february.expenses == 0.0
    assert february.net_balance == 500.0
    assert february.transferred == 0.0


def test_annual_overview_income_vs_expenses_by_month_matches_month_by_month_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)

    assert overview.income_vs_expenses_by_month == overview.month_by_month


def test_financial_year_transactions_with_month_1_does_not_span_two_calendar_years(tmp_path: Path, make_candidate):
    store = connect(tmp_path / "budget.db")
    store.append_rows(
        [
            make_candidate(date=date(2025, 12, 31), notes="Last day of 2025"),
            make_candidate(date=date(2026, 1, 1), notes="First day of 2026"),
            make_candidate(date=date(2026, 12, 31), notes="Last day of 2026"),
            make_candidate(date=date(2027, 1, 1), notes="First day of 2027"),
        ]
    )

    notes = {t.notes for t in get_financial_year_transactions(store, year=2026, month=1)}

    assert notes == {"First day of 2026", "Last day of 2026"}


def test_full_year_grid_has_twelve_amounts_per_row_in_january_to_december_order_for_calendar_year(fake_store):
    store = fake_store(
        category_budgets={
            ("Groceries", 2026, 1): 300.0,
            ("Groceries", 2026, 12): 350.0,
        }
    )

    rows = get_full_year_budget_grid(store, year=2026, start_month=1)
    groceries = next(row for row in rows if row.category == "Groceries")

    assert len(groceries.amounts) == 12
    assert groceries.amounts[0] == 300.0  # January
    assert groceries.amounts[11] == 350.0  # December
    assert groceries.amounts[1:11] == [None] * 10


def test_full_year_grid_a_category_budget_outside_the_calendar_year_is_not_included(fake_store):
    # December 2025 is the tail of the previous Calendar Year, not the one
    # starting 2026-01 - it must not leak into this grid's January slot.
    store = fake_store(category_budgets={("Groceries", 2025, 12): 999.0})

    rows = get_full_year_budget_grid(store, year=2026, start_month=1)
    groceries = next(row for row in rows if row.category == "Groceries")

    assert all(amount is None for amount in groceries.amounts)


def test_transaction_date_range_on_an_empty_log_is_none_and_none(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    assert get_transaction_date_range(store) == (None, None)


def test_transaction_date_range_is_the_earliest_and_latest_transaction_dates(tmp_path: Path, make_candidate):
    store = connect(tmp_path / "budget.db")
    store.append_rows(
        [
            make_candidate(date=date(2026, 6, 30)),
            make_candidate(date=date(2026, 8, 3)),
            make_candidate(date=date(2026, 7, 15)),
        ]
    )

    assert get_transaction_date_range(store) == (date(2026, 6, 30), date(2026, 8, 3))


def _insert_transaction(database_path: Path, **fields) -> None:
    # Transfer has no seeded Category (CONTEXT.md - added lazily, only for
    # real cases), so this also seeds whichever ad hoc Category the test
    # names (e.g. "Savings") the way a user would via Category Management.
    connection = sqlite3.connect(database_path)
    connection.execute(
        "INSERT OR IGNORE INTO categories (type, name) VALUES (:type, :category)", fields
    )
    connection.execute(
        "INSERT INTO transactions (date, amount, type, category_id, notes) "
        "VALUES (:date, :amount, :type, (SELECT id FROM categories WHERE name = :category), :notes)",
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


def test_transactions_in_range_on_an_empty_database_returns_no_transactions(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    assert get_transactions_in_range(store, date(2026, 7, 1), date(2027, 6, 30)) == []


def test_transactions_in_range_includes_both_bounds(tmp_path: Path, make_candidate):
    store = connect(tmp_path / "budget.db")
    store.append_rows(
        [
            make_candidate(date=date(2026, 7, 31), notes="Before the range"),
            make_candidate(date=date(2026, 8, 1), notes="Start of the range"),
            make_candidate(date=date(2026, 8, 15), notes="Inside the range"),
            make_candidate(date=date(2026, 8, 31), notes="End of the range"),
            make_candidate(date=date(2026, 9, 1), notes="After the range"),
        ]
    )

    notes = {t.notes for t in get_transactions_in_range(store, date(2026, 8, 1), date(2026, 8, 31))}

    assert notes == {"Start of the range", "Inside the range", "End of the range"}


def test_transactions_in_range_spans_a_financial_year_boundary(tmp_path: Path, make_candidate):
    store = connect(tmp_path / "budget.db")
    store.append_rows(
        [
            make_candidate(date=date(2026, 6, 15), notes="Prior Financial Year"),
            make_candidate(date=date(2026, 6, 30), notes="Last day of FY25-26"),
            make_candidate(date=date(2026, 7, 1), notes="First day of FY26-27"),
            make_candidate(date=date(2026, 7, 15), notes="Next Financial Year"),
        ]
    )

    notes = {t.notes for t in get_transactions_in_range(store, date(2026, 6, 30), date(2026, 7, 1))}

    assert notes == {"Last day of FY25-26", "First day of FY26-27"}


def test_transactions_in_range_are_sorted_newest_first(tmp_path: Path, make_candidate):
    store = connect(tmp_path / "budget.db")
    store.append_rows(
        [
            make_candidate(date=date(2026, 8, 1), notes="Oldest"),
            make_candidate(date=date(2026, 8, 20), notes="Newest"),
            make_candidate(date=date(2026, 8, 10), notes="Middle"),
        ]
    )

    ordered = get_transactions_in_range(store, date(2026, 8, 1), date(2026, 8, 31))

    assert [t.notes for t in ordered] == ["Newest", "Middle", "Oldest"]


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


# — get_budget_editor (Budget tab historical columns, Issue #63) —


def test_budget_editor_includes_every_budgetable_category_grouped_by_type_not_transfer(fake_store):
    store = fake_store()

    rows = get_budget_editor(store, year=2026, month=8)

    assert {row.type for row in rows} == {"Income", "Expense", "Debt"}
    assert "Salary" in {row.category for row in rows}
    assert "Mortgage Repayment" in {row.category for row in rows}


def test_budget_editor_includes_a_category_added_through_category_management(fake_store):
    # Issue #90 - Category/Type pairs are read from the live `categories`
    # table, not the hardcoded CATEGORIES_BY_TYPE dict, so a Category added
    # via Category Management (#91) shows up in the editor immediately.
    store = fake_store()
    store.create_category("Expense", "Pet Care", None)

    rows = get_budget_editor(store, year=2026, month=8)

    assert ("Expense", "Pet Care") in {(row.type, row.category) for row in rows}


def test_budget_editor_reports_this_months_budgeted_amount_or_none_if_unset(fake_store):
    store = fake_store(category_budgets={("Groceries", 2026, 8): 320.0})

    rows = get_budget_editor(store, year=2026, month=8)
    by_category = {row.category: row for row in rows}

    assert by_category["Groceries"].budgeted == 320.0
    assert by_category["Transport"].budgeted is None


def test_budget_editor_last_month_actual_is_last_calendar_months_total_for_the_category(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 15), amount=270.0, type="Expense", category="Groceries", notes="Coles"),
            make_transaction(date=date(2026, 6, 15), amount=999.0, type="Expense", category="Groceries", notes="Older"),
        ],
    )

    rows = get_budget_editor(store, year=2026, month=8, trailing_months=3)
    by_category = {row.category: row for row in rows}

    assert by_category["Groceries"].last_month_actual == 270.0


def test_budget_editor_last_month_budgeted_is_last_calendar_months_category_budget_or_none_if_unset(fake_store):
    store = fake_store(category_budgets={("Groceries", 2026, 7): 300.0})

    rows = get_budget_editor(store, year=2026, month=8, trailing_months=3)
    by_category = {row.category: row for row in rows}

    assert by_category["Groceries"].last_month_budgeted == 300.0
    assert by_category["Transport"].last_month_budgeted is None


def test_budget_editor_last_month_budgeted_ignores_this_months_own_budget(fake_store):
    store = fake_store(category_budgets={("Groceries", 2026, 8): 650.0})

    rows = get_budget_editor(store, year=2026, month=8, trailing_months=3)
    by_category = {row.category: row for row in rows}

    assert by_category["Groceries"].last_month_budgeted is None


def test_budget_editor_last_month_budgeted_crosses_the_financial_year_boundary(fake_store):
    store = fake_store(category_budgets={("Groceries", 2026, 6): 280.0})

    rows = get_budget_editor(store, year=2026, month=7, trailing_months=3)
    by_category = {row.category: row for row in rows}

    assert by_category["Groceries"].last_month_budgeted == 280.0


def test_budget_editor_trailing_average_and_variance_over_a_window_with_sufficient_history(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 5, 1), amount=300.0, type="Expense", category="Groceries", notes="May"),
            make_transaction(date=date(2026, 6, 1), amount=330.0, type="Expense", category="Groceries", notes="Jun"),
            make_transaction(date=date(2026, 7, 1), amount=270.0, type="Expense", category="Groceries", notes="Jul"),
        ],
        category_budgets={
            ("Groceries", 2026, 5): 300.0,
            ("Groceries", 2026, 6): 300.0,
            ("Groceries", 2026, 7): 300.0,
            ("Groceries", 2026, 8): 320.0,
        },
    )

    rows = get_budget_editor(store, year=2026, month=8, trailing_months=3)
    groceries = next(row for row in rows if row.category == "Groceries")

    assert groceries.last_month_actual == 270.0
    assert groceries.trailing_average_actual == 300.0  # (300 + 330 + 270) / 3
    assert groceries.average_variance_pct == 0.0  # variances of 0%, +10%, -10% average to 0%


def test_budget_editor_windowed_columns_are_unset_with_insufficient_history(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 15), amount=270.0, type="Expense", category="Groceries", notes="Coles"),
        ],
    )

    rows = get_budget_editor(store, year=2026, month=8, trailing_months=3)
    groceries = next(row for row in rows if row.category == "Groceries")

    # Only one prior month of Transaction history exists, short of the
    # 3-month window - so the windowed columns are unset, not a
    # misleadingly small average built from one month.
    assert groceries.last_month_actual == 270.0
    assert groceries.trailing_average_actual is None
    assert groceries.average_variance_pct is None


def test_budget_editor_insufficient_history_is_checked_per_category_not_store_wide(fake_store, make_transaction):
    # Groceries has 3 full months of history within the window; Salary has
    # none at all. A store-wide check would treat Salary as sufficient too
    # (since some Category does have 3 months of data) and report a
    # misleadingly real-looking $0 average - the per-Category check must not.
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 5, 1), amount=300.0, type="Expense", category="Groceries", notes="May"),
            make_transaction(date=date(2026, 6, 1), amount=330.0, type="Expense", category="Groceries", notes="Jun"),
            make_transaction(date=date(2026, 7, 1), amount=270.0, type="Expense", category="Groceries", notes="Jul"),
        ],
    )

    rows = get_budget_editor(store, year=2026, month=8, trailing_months=3)
    by_category = {row.category: row for row in rows}

    assert by_category["Groceries"].trailing_average_actual == 300.0
    assert by_category["Salary"].trailing_average_actual is None
    assert by_category["Salary"].average_variance_pct is None


def test_budget_editor_average_variance_is_unset_when_no_window_month_was_budgeted(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 5, 1), amount=300.0, type="Expense", category="Groceries", notes="May"),
            make_transaction(date=date(2026, 6, 1), amount=330.0, type="Expense", category="Groceries", notes="Jun"),
            make_transaction(date=date(2026, 7, 1), amount=270.0, type="Expense", category="Groceries", notes="Jul"),
        ],
    )

    rows = get_budget_editor(store, year=2026, month=8, trailing_months=3)
    groceries = next(row for row in rows if row.category == "Groceries")

    assert groceries.trailing_average_actual == 300.0
    assert groceries.average_variance_pct is None


def test_budget_editor_a_month_with_no_transactions_or_budgets_is_a_coherent_empty_state(fake_store):
    store = fake_store()

    rows = get_budget_editor(store, year=2026, month=8, trailing_months=3)

    assert all(row.budgeted is None for row in rows)
    assert all(row.last_month_actual == 0.0 for row in rows)
    assert all(row.trailing_average_actual is None for row in rows)
    assert all(row.average_variance_pct is None for row in rows)


def test_budget_editor_rejects_a_trailing_window_outside_3_6_12(fake_store):
    store = fake_store()

    with pytest.raises(ValueError):
        get_budget_editor(store, year=2026, month=8, trailing_months=4)


# — get_full_year_budget_grid (Budget tab Full year read-only grid, Issue #64) —


def test_full_year_grid_includes_every_budgetable_category_grouped_by_type_not_transfer(fake_store):
    store = fake_store()

    rows = get_full_year_budget_grid(store, year=2026)

    assert {row.type for row in rows} == {"Income", "Expense", "Debt"}
    assert "Salary" in {row.category for row in rows}
    assert "Mortgage Repayment" in {row.category for row in rows}


def test_full_year_grid_has_twelve_amounts_per_row_in_july_to_june_order(fake_store):
    store = fake_store(
        category_budgets={
            ("Groceries", 2026, 7): 300.0,
            ("Groceries", 2027, 6): 350.0,
        }
    )

    rows = get_full_year_budget_grid(store, year=2026)
    groceries = next(row for row in rows if row.category == "Groceries")

    assert len(groceries.amounts) == 12
    assert groceries.amounts[0] == 300.0  # July
    assert groceries.amounts[11] == 350.0  # June
    assert groceries.amounts[1:11] == [None] * 10


def test_full_year_grid_a_category_budget_outside_the_financial_year_is_not_included(fake_store):
    # June 2026 is the tail of the *previous* Financial Year (2025), not the
    # one starting 2026-07 - it must not leak into this grid's July slot.
    store = fake_store(category_budgets={("Groceries", 2026, 6): 999.0})

    rows = get_full_year_budget_grid(store, year=2026)
    groceries = next(row for row in rows if row.category == "Groceries")

    assert all(amount is None for amount in groceries.amounts)


def test_full_year_grid_a_month_with_no_budget_set_is_none_not_zero(fake_store):
    store = fake_store()

    rows = get_full_year_budget_grid(store, year=2026)

    assert all(amount is None for row in rows for amount in row.amounts)
