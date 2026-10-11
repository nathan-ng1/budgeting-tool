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
    assert overview.stat_tiles.available_to_save == 0
    assert overview.stat_tiles.saved == 0
    assert overview.spending_by_category == []
    assert overview.budgeted_vs_actual == []
    assert overview.debt_summary == []
    assert overview.top_merchants == []
    assert overview.spending_over_time.total == 0
    assert overview.spending_over_time.daily_average == 0
    assert len(overview.spending_over_time.daily) == 31  # every day of August


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
    _insert_transaction(database_path, date="2026-08-06", amount=500.0, type="Savings", category="Savings", notes="To savings")

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.stat_tiles.income == 4100.0
    assert overview.stat_tiles.expenses == 250.0
    assert overview.stat_tiles.debt == 875.0
    assert overview.stat_tiles.saved == 500.0


def test_available_to_save_includes_savings(tmp_path: Path, make_candidate):
    # ADR-0022 - money moved to Savings is never subtracted, so it still
    # counts toward this figure.
    database_path = tmp_path / "budget.db"
    store = connect(database_path)
    store.append_rows(
        [
            make_candidate(date=date(2026, 8, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_candidate(date=date(2026, 8, 2), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
        ]
    )
    _insert_transaction(database_path, date="2026-08-03", amount=5000.0, type="Savings", category="Savings", notes="To savings")

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.stat_tiles.available_to_save == 700.0


def test_available_to_save_subtracts_debt(tmp_path: Path, make_candidate):
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

    assert overview.stat_tiles.available_to_save == 500.0


def test_stat_tiles_sum_bills_and_subscriptions(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=80.0, type="Bills & Subscriptions", category="Phone Plan", notes="Telstra"),
            make_transaction(date=date(2026, 8, 2), amount=70.0, type="Bills & Subscriptions", category="Internet", notes="Aussie BB"),
            make_transaction(date=date(2026, 8, 3), amount=200.0, type="Expense", category="Groceries", notes="Woolworths"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.stat_tiles.bills_subscriptions == 150.0
    assert overview.stat_tiles.expenses == 200.0


def test_available_to_save_subtracts_bills_and_subscriptions(fake_store, make_transaction):
    # ADR-0024 - Available to Save is Income - Expenses - Debt - Bills & Subscriptions.
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 8, 2), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 3), amount=200.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 8, 4), amount=150.0, type="Bills & Subscriptions", category="Insurance", notes="NRMA"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.stat_tiles.available_to_save == 350.0


@pytest.mark.parametrize(
    ("saved", "expected_unallocated"),
    [
        (100.0, 250.0),  # money left without a job
        (350.0, 0.0),  # every dollar allocated - Balanced
        (500.0, -150.0),  # Savings dipped into existing funds - Over income
    ],
)
def test_unallocated_is_available_to_save_minus_saved_signed_and_never_clamped(
    fake_store, make_transaction, saved, expected_unallocated
):
    # #168 - Unallocated is Income - Expenses - Bills & Subscriptions - Debt -
    # Savings (GLOSSARY.md); unlike the allocation bar it goes negative.
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 8, 2), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 3), amount=200.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 8, 4), amount=150.0, type="Bills & Subscriptions", category="Insurance", notes="NRMA"),
            make_transaction(date=date(2026, 8, 5), amount=saved, type="Savings", category="Savings", notes="To savings"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.stat_tiles.available_to_save == 350.0
    assert overview.stat_tiles.unallocated == expected_unallocated


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


def test_income_allocation_splits_expenses_saved_and_unallocated_as_pct_of_income(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 8, 2), amount=400.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 3), amount=100.0, type="Savings", category="Savings", notes="To savings"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)
    allocation = overview.income_allocation

    assert allocation.expenses_amount == 400.0
    assert allocation.expenses_pct == 40.0
    assert allocation.saved_amount == 100.0
    assert allocation.saved_pct == 10.0
    assert allocation.unallocated_amount == 500.0
    assert allocation.unallocated_pct == 50.0
    assert allocation.over_income_amount == 0.0
    assert allocation.over_income_pct == 0.0


def test_income_allocation_includes_a_debt_share_of_income(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 8, 2), amount=400.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 3), amount=200.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 8, 4), amount=100.0, type="Savings", category="Savings", notes="To savings"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)
    allocation = overview.income_allocation

    assert allocation.debt_amount == 200.0
    assert allocation.debt_pct == 20.0
    assert allocation.unallocated_amount == 300.0
    assert allocation.unallocated_pct == 30.0


def test_income_allocation_includes_a_bills_and_subscriptions_share_of_income(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 8, 2), amount=400.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 3), amount=150.0, type="Bills & Subscriptions", category="Insurance", notes="NRMA"),
            make_transaction(date=date(2026, 8, 4), amount=100.0, type="Savings", category="Savings", notes="To savings"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)
    allocation = overview.income_allocation

    assert allocation.bills_subscriptions_amount == 150.0
    assert allocation.bills_subscriptions_pct == 15.0
    assert allocation.unallocated_amount == 350.0
    assert allocation.unallocated_pct == 35.0


def test_income_allocation_counts_bills_and_subscriptions_toward_over_income(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 8, 2), amount=900.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 3), amount=300.0, type="Bills & Subscriptions", category="Insurance", notes="NRMA"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.income_allocation.over_income_amount == 200.0
    assert overview.income_allocation.over_income_pct == 20.0


def test_income_allocation_reports_over_income_excess_when_outflows_exceed_income(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 8, 2), amount=900.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 3), amount=300.0, type="Savings", category="Savings", notes="To savings"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)
    allocation = overview.income_allocation

    # Unallocated is -200 here; the bar clamps its segment at 0 and reports
    # the overage as Over income instead (#168).
    assert allocation.unallocated_amount == 0.0
    assert allocation.unallocated_pct == 0.0
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
    assert allocation.bills_subscriptions_pct == 0.0
    assert allocation.saved_pct == 0.0
    assert allocation.unallocated_pct == 0.0
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
        CategorySpend(category="Groceries", type="Expense", amount=400.0, pct_of_spending=80.0),
        CategorySpend(category="Transport", type="Expense", amount=100.0, pct_of_spending=20.0),
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
        CategorySpend(category="Groceries", type="Expense", amount=300.0, pct_of_spending=100.0),
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


def test_budgeted_vs_actual_includes_savings_categories(fake_store, make_transaction):
    # Issue #136 - Category Budget extends to Savings, the same round-trip
    # already proven for Income/Expense/Debt above.
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 3), amount=600.0, type="Savings", category="Savings", notes="To savings"),
        ],
        category_budgets={("Savings", 2026, 8): 500.0},
    )

    overview = get_month_overview(store, year=2026, month=8)
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Savings"].type == "Savings"
    assert by_category["Savings"].budgeted == 500.0
    assert by_category["Savings"].actual == 600.0
    assert by_category["Savings"].diff == -100.0


def test_budgeted_vs_actual_includes_bills_and_subscriptions_categories(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 3), amount=95.0, type="Bills & Subscriptions", category="Phone Plan", notes="Telstra"),
        ],
        category_budgets={("Phone Plan", 2026, 8): 80.0},
    )

    overview = get_month_overview(store, year=2026, month=8)
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Phone Plan"].type == "Bills & Subscriptions"
    assert by_category["Phone Plan"].budgeted == 80.0
    assert by_category["Phone Plan"].actual == 95.0
    assert by_category["Phone Plan"].diff == -15.0


def tx(make_transaction, day, amount, notes, category="Groceries", type="Expense", month=8, id=1):
    return make_transaction(
        id=id, date=date(2026, month, day), amount=amount, type=type, category=category, notes=notes
    )


def test_top_merchants_are_the_five_largest_that_month_descending(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            tx(make_transaction, 1, 10.0, "A"),
            tx(make_transaction, 2, 90.0, "B"),
            tx(make_transaction, 3, 50.0, "C"),
            tx(make_transaction, 4, 70.0, "D"),
            tx(make_transaction, 5, 60.0, "E"),
            tx(make_transaction, 6, 40.0, "F"),
            tx(make_transaction, 7, 1000.0, "Employer", category="Salary", type="Income"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert [row.total for row in overview.top_merchants] == [90.0, 70.0, 60.0, 50.0, 40.0]
    assert [row.merchant for row in overview.top_merchants] == ["B", "D", "E", "C", "F"]


def test_top_merchants_group_case_digit_and_spacing_variants_into_one_merchant(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            tx(make_transaction, 1, 30.0, "WOOLWORTHS 1234", id=1),
            tx(make_transaction, 9, 20.0, "Woolworths  5678", id=2),
            tx(make_transaction, 5, 10.0, "woolworths", id=3),
            tx(make_transaction, 2, 25.0, "Coles", id=4),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert len(overview.top_merchants) == 2
    woolworths = overview.top_merchants[0]
    assert woolworths.merchant == "Woolworths  5678"  # most recent original Notes
    assert woolworths.total == 60.0
    assert woolworths.count == 3


def test_top_merchants_category_is_that_of_the_most_recent_transaction(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            tx(make_transaction, 1, 10.0, "Kmart", category="Shopping & Retail", id=1),
            tx(make_transaction, 8, 10.0, "Kmart", category="Entertainment & Leisure", id=2),
            tx(make_transaction, 3, 10.0, "Kmart", category="Groceries", id=3),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.top_merchants[0].category == "Entertainment & Leisure"


def test_top_merchants_tiebreak_by_name(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            tx(make_transaction, 5, 50.0, "Zebra"),
            tx(make_transaction, 1, 50.0, "Apple"),
            tx(make_transaction, 1, 50.0, "banana"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert [row.merchant for row in overview.top_merchants] == ["Apple", "banana", "Zebra"]


def test_top_merchants_exclude_debt_and_beem_adjustment_but_include_bills_and_subscriptions(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            tx(make_transaction, 1, 10.0, "A"),
            tx(make_transaction, 2, 875.0, "Werribee", category="Mortgage Repayment", type="Debt"),
            tx(make_transaction, 3, -500.0, "Beem credit", category="Beem Adjustment"),
            tx(make_transaction, 4, 120.0, "AGL", category="Internet", type="Bills & Subscriptions"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert [row.merchant for row in overview.top_merchants] == ["AGL", "A"]


def test_top_merchants_group_outgoing_beem_payments_by_notes(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            tx(make_transaction, 1, 40.0, "Beem to Sam", category="Dining & Takeaway", id=1),
            tx(make_transaction, 2, 15.0, "Beem to Sam", category="Dining & Takeaway", id=2),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert [(row.merchant, row.total, row.count) for row in overview.top_merchants] == [("Beem to Sam", 55.0, 2)]


def test_top_merchants_group_digit_only_notes_by_the_stripped_lowercased_notes(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            tx(make_transaction, 1, 10.0, "1234", id=1),
            tx(make_transaction, 2, 20.0, "5678", id=2),
            tx(make_transaction, 3, 5.0, "1234 ", id=3),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert [(row.merchant, row.total, row.count) for row in overview.top_merchants] == [
        ("5678", 20.0, 1),
        ("1234 ", 15.0, 2),
    ]


def test_spending_over_time_is_a_cumulative_daily_total_for_every_day_of_the_month(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=100.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 3), amount=50.0, type="Expense", category="Transport", notes="Fuel"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)
    daily = overview.spending_over_time.daily

    assert len(daily) == 31
    assert daily[0].date == "2026-08-01"
    assert daily[0].cumulative == 100.0
    assert daily[1].cumulative == 100.0  # no transaction on day 2 - carries forward
    assert daily[2].cumulative == 150.0
    assert daily[-1].cumulative == 150.0
    assert overview.spending_over_time.total == 150.0
    assert overview.spending_over_time.daily_average == round(150.0 / 31, 2)


def test_spending_over_time_excludes_debt(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=100.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 3), amount=875.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.spending_over_time.total == 100.0


def test_annual_overview_before_the_financial_year_starts_elapses_no_months(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    overview = get_annual_overview(store, year=2026, today=date(2026, 6, 15))

    assert overview.year == 2026
    assert overview.elapsed_months == 0
    assert overview.stat_tiles.income == 0
    assert overview.monthly_average.income == 0
    assert overview.top_merchants == []


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


def test_annual_overview_stat_tiles_and_monthly_average_include_bills_and_subscriptions(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 7, 1), amount=120.0, type="Bills & Subscriptions", category="Internet", notes="Aussie BB"),
            make_transaction(date=date(2026, 8, 1), amount=80.0, type="Bills & Subscriptions", category="Internet", notes="Aussie BB"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert overview.stat_tiles.bills_subscriptions == 200.0
    assert overview.stat_tiles.available_to_save == 800.0
    assert overview.monthly_average.bills_subscriptions == 100.0
    assert overview.income_allocation.bills_subscriptions_amount == 200.0
    assert overview.income_allocation.bills_subscriptions_pct == 20.0


def test_annual_overview_stat_tiles_and_monthly_average_include_unallocated(fake_store, make_transaction):
    # #168 - the year-to-date total is signed like the month figure, and the
    # average divides it by elapsed months like every other tile.
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 7, 2), amount=700.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 7, 3), amount=500.0, type="Savings", category="Savings", notes="To savings"),
            make_transaction(date=date(2026, 8, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 8, 2), amount=200.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 3), amount=900.0, type="Savings", category="Savings", notes="To savings"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert overview.stat_tiles.available_to_save == 1100.0
    assert overview.stat_tiles.unallocated == -300.0
    assert overview.monthly_average.unallocated == -150.0


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
        CategorySpend(category="Groceries", type="Expense", amount=400.0, pct_of_spending=80.0),
        CategorySpend(category="Transport", type="Expense", amount=100.0, pct_of_spending=20.0),
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
        CategorySpend(category="Groceries", type="Expense", amount=300.0, pct_of_spending=100.0),
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


def test_annual_overview_budgeted_vs_actual_includes_savings_categories_summed_across_elapsed_months(
    fake_store, make_transaction
):
    # Issue #136 - the annual sum-over-elapsed-months behaviour already
    # proven for Income/Expense/Debt applies to Savings too.
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 3), amount=500.0, type="Savings", category="Savings", notes="To savings"),
            make_transaction(date=date(2026, 8, 3), amount=600.0, type="Savings", category="Savings", notes="To savings"),
        ],
        category_budgets={("Savings", 2026, 7): 400.0, ("Savings", 2026, 8): 400.0},
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 15))
    by_category = {row.category: row for row in overview.budgeted_vs_actual}

    assert by_category["Savings"].type == "Savings"
    assert by_category["Savings"].budgeted == 800.0
    assert by_category["Savings"].actual == 1100.0


def test_annual_overview_top_merchants_are_the_ten_largest_across_elapsed_months(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            tx(make_transaction, d, amount, "Merchant " + "ABCDEFGHIJK"[d - 1], month=7)
            for d, amount in enumerate([10.0, 90.0, 50.0, 70.0, 60.0, 40.0, 30.0, 20.0, 80.0, 100.0, 110.0], start=1)
        ]
        + [tx(make_transaction, 1, 1000.0, "Employer", category="Salary", type="Income", month=8)]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert len(overview.top_merchants) == 10
    assert [row.total for row in overview.top_merchants] == [110.0, 100.0, 90.0, 80.0, 70.0, 60.0, 50.0, 40.0, 30.0, 20.0]


def test_annual_overview_top_merchants_group_across_months_and_exclude_debt_and_beem_adjustment(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            tx(make_transaction, 1, 10.0, "Woolworths 1", month=7, id=1),
            tx(make_transaction, 2, 15.0, "WOOLWORTHS 2", month=8, id=2),
            tx(make_transaction, 3, 875.0, "Werribee", category="Mortgage Repayment", type="Debt", month=7, id=3),
            tx(make_transaction, 4, -9.0, "Beem credit", category="Beem Adjustment", month=7, id=4),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert [(row.merchant, row.total, row.count) for row in overview.top_merchants] == [("WOOLWORTHS 2", 25.0, 2)]


def test_annual_overview_top_merchants_exclude_transactions_from_months_not_yet_elapsed(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            tx(make_transaction, 5, 500.0, "Elapsed", month=7),
            tx(make_transaction, 1, 999.0, "Not yet elapsed", month=8),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 7, 21))

    assert [row.merchant for row in overview.top_merchants] == ["Elapsed"]


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
            make_transaction(date=date(2026, 7, 3), amount=100.0, type="Savings", category="Savings", notes="To savings"),
            make_transaction(date=date(2026, 8, 5), amount=500.0, type="Income", category="Salary", notes="Employer"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))
    by_month = {(row.year, row.month): row for row in overview.month_by_month}

    july = by_month[(2026, 7)]
    assert july.income == 1000.0
    assert july.expenses == 400.0
    assert july.debt == 150.0
    assert july.available_to_save == 450.0
    assert july.saved == 100.0

    august = by_month[(2026, 8)]
    assert august.income == 500.0
    assert august.expenses == 0.0
    assert august.available_to_save == 500.0
    assert august.saved == 0.0


def test_annual_overview_month_by_month_includes_bills_and_subscriptions_in_each_months_net(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 7, 2), amount=60.0, type="Bills & Subscriptions", category="Phone Plan", notes="Telstra"),
            make_transaction(date=date(2026, 8, 2), amount=700.0, type="Bills & Subscriptions", category="Car Registration", notes="VicRoads"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))
    by_month = {(row.year, row.month): row for row in overview.month_by_month}

    assert by_month[(2026, 7)].bills_subscriptions == 60.0
    assert by_month[(2026, 7)].available_to_save == 940.0
    assert by_month[(2026, 8)].bills_subscriptions == 700.0
    assert by_month[(2026, 8)].available_to_save == -700.0


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
        year=2026, month=9, income=0.0, expenses=0.0, bills_subscriptions=0.0, debt=0.0, available_to_save=0.0, saved=0.0
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
        year=2026, month=3, income=0.0, expenses=0.0, bills_subscriptions=0.0, debt=0.0, available_to_save=0.0, saved=0.0
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
        CategorySpend(category="Groceries", type="Expense", amount=400.0, pct_of_spending=80.0),
        CategorySpend(category="Transport", type="Expense", amount=100.0, pct_of_spending=20.0),
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
        CategorySpend(category="Groceries", type="Expense", amount=300.0, pct_of_spending=100.0),
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


def test_annual_overview_top_merchants_are_the_ten_largest_across_elapsed_months_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            tx(make_transaction, d, amount, "Merchant " + "ABCDEFGHIJK"[d - 1], month=1)
            for d, amount in enumerate([10.0, 90.0, 50.0, 70.0, 60.0, 40.0, 30.0, 20.0, 80.0, 100.0, 110.0], start=1)
        ]
        + [tx(make_transaction, 1, 1000.0, "Employer", category="Salary", type="Income", month=2)]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)

    assert len(overview.top_merchants) == 10
    assert [row.total for row in overview.top_merchants] == [110.0, 100.0, 90.0, 80.0, 70.0, 60.0, 50.0, 40.0, 30.0, 20.0]


def test_annual_overview_top_merchants_group_across_months_and_exclude_debt_and_beem_adjustment_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            tx(make_transaction, 1, 10.0, "Woolworths 1", month=1, id=1),
            tx(make_transaction, 2, 15.0, "WOOLWORTHS 2", month=2, id=2),
            tx(make_transaction, 3, 875.0, "Werribee", category="Mortgage Repayment", type="Debt", month=1, id=3),
            tx(make_transaction, 4, -9.0, "Beem credit", category="Beem Adjustment", month=1, id=4),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)

    assert [(row.merchant, row.total, row.count) for row in overview.top_merchants] == [("WOOLWORTHS 2", 25.0, 2)]


def test_annual_overview_top_merchants_exclude_transactions_from_months_not_yet_elapsed_for_calendar_year(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            tx(make_transaction, 5, 500.0, "Elapsed", month=1),
            tx(make_transaction, 1, 999.0, "Not yet elapsed", month=2),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 1, 21), start_month=1)

    assert [row.merchant for row in overview.top_merchants] == ["Elapsed"]


def test_annual_overview_month_by_month_sums_each_month_independently_for_calendar_year(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 1, 1), amount=1000.0, type="Income", category="Salary", notes="Employer"),
            make_transaction(date=date(2026, 1, 2), amount=400.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 1, 2), amount=150.0, type="Debt", category="Mortgage Repayment", notes="Repayment"),
            make_transaction(date=date(2026, 1, 3), amount=100.0, type="Savings", category="Savings", notes="To savings"),
            make_transaction(date=date(2026, 2, 5), amount=500.0, type="Income", category="Salary", notes="Employer"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 2, 21), start_month=1)
    by_month = {(row.year, row.month): row for row in overview.month_by_month}

    january = by_month[(2026, 1)]
    assert january.income == 1000.0
    assert january.expenses == 400.0
    assert january.debt == 150.0
    assert january.available_to_save == 450.0
    assert january.saved == 100.0

    february = by_month[(2026, 2)]
    assert february.income == 500.0
    assert february.expenses == 0.0
    assert february.available_to_save == 500.0
    assert february.saved == 0.0


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
    # INSERT OR IGNORE so this also seeds whichever ad hoc Category the test
    # names, the way a user would via Category Management - a no-op for a
    # Category already seeded (e.g. Savings' own predefined Categories).
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
    # The "As at" line says how current the Transaction Log is, so a Savings
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

    assert {row.type for row in rows} == {"Income", "Expense", "Bills & Subscriptions", "Debt", "Savings"}
    assert "Salary" in {row.category for row in rows}
    assert "Mortgage Repayment" in {row.category for row in rows}
    assert "Savings" in {row.category for row in rows}


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


def test_budget_editor_reports_a_savings_category_budgeted_amount(fake_store, make_transaction):
    # Issue #136 - a Savings Category Budget round-trips through
    # get_budget_editor exactly like Income/Expense/Debt.
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 5), amount=600.0, type="Savings", category="Savings", notes="To savings"),
        ],
        category_budgets={("Savings", 2026, 8): 500.0},
    )

    rows = get_budget_editor(store, year=2026, month=8)
    by_category = {row.category: row for row in rows}

    assert by_category["Savings"].type == "Savings"
    assert by_category["Savings"].budgeted == 500.0
    assert by_category["Savings"].month_actual == 600.0


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


def test_budget_editor_month_actual_is_the_selected_months_own_total_for_the_category(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 10), amount=310.0, type="Expense", category="Groceries", notes="Woolies"),
            make_transaction(date=date(2026, 7, 15), amount=270.0, type="Expense", category="Groceries", notes="Coles"),
        ],
    )

    rows = get_budget_editor(store, year=2026, month=8, trailing_months=3)
    by_category = {row.category: row for row in rows}

    # month_actual reflects the selected (year, month), distinct from
    # last_month_actual which always reflects the prior calendar month.
    assert by_category["Groceries"].month_actual == 310.0
    assert by_category["Groceries"].last_month_actual == 270.0


def test_budget_editor_month_actual_is_zero_for_a_month_with_no_transactions(fake_store):
    store = fake_store()

    rows = get_budget_editor(store, year=2026, month=8, trailing_months=3)
    by_category = {row.category: row for row in rows}

    # Always a real, computable figure - $0, never unset (unlike the
    # windowed trailing columns, which can read as insufficient history).
    assert by_category["Groceries"].month_actual == 0.0


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
    assert all(row.month_actual == 0.0 for row in rows)


def test_budget_editor_rejects_a_trailing_window_outside_3_6_12(fake_store):
    store = fake_store()

    with pytest.raises(ValueError):
        get_budget_editor(store, year=2026, month=8, trailing_months=4)


# — get_full_year_budget_grid (Budget tab Full year read-only grid, Issue #64) —


def test_full_year_grid_includes_every_budgetable_category_grouped_by_type_not_transfer(fake_store):
    store = fake_store()

    rows = get_full_year_budget_grid(store, year=2026)

    assert {row.type for row in rows} == {"Income", "Expense", "Bills & Subscriptions", "Debt", "Savings"}
    assert "Salary" in {row.category for row in rows}
    assert "Mortgage Repayment" in {row.category for row in rows}
    assert "Savings" in {row.category for row in rows}


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


def test_full_year_grid_reports_a_savings_category_budget(fake_store):
    # Issue #136 - a Savings Category Budget round-trips through
    # get_full_year_budget_grid exactly like Income/Expense/Debt.
    store = fake_store(category_budgets={("Savings", 2026, 7): 500.0})

    rows = get_full_year_budget_grid(store, year=2026)
    savings = next(row for row in rows if row.category == "Savings")

    assert savings.type == "Savings"
    assert savings.amounts[0] == 500.0  # July


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


def test_spending_over_time_counts_bills_and_subscriptions_but_not_debt_or_savings(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=100.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 10), amount=620.0, type="Bills & Subscriptions", category="Insurance", notes="Annual cover"),
            make_transaction(date=date(2026, 8, 3), amount=875.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
            make_transaction(date=date(2026, 8, 4), amount=500.0, type="Savings", category="Savings", notes="Transfer"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)
    daily = overview.spending_over_time.daily

    assert overview.spending_over_time.total == 720.0
    assert overview.spending_over_time.daily_average == round(720.0 / 31, 2)
    assert daily[8].cumulative == 100.0
    assert daily[9].cumulative == 720.0  # the lumpy bill is a step


def test_spending_over_time_is_reduced_by_beem_adjustment_reimbursements(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=100.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 2), amount=-30.0, type="Expense", category="Beem Adjustment", notes="Beem"),
        ]
    )

    assert get_month_overview(store, year=2026, month=8).spending_over_time.total == 70.0


def test_spending_by_category_lists_bills_and_subscriptions_with_shares_of_spending(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 8, 1), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 2), amount=100.0, type="Bills & Subscriptions", category="Internet", notes="ISP"),
            make_transaction(date=date(2026, 8, 3), amount=875.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ]
    )

    overview = get_month_overview(store, year=2026, month=8)

    assert overview.spending_by_category == [
        CategorySpend(category="Groceries", type="Expense", amount=300.0, pct_of_spending=75.0),
        CategorySpend(category="Internet", type="Bills & Subscriptions", amount=100.0, pct_of_spending=25.0),
    ]
    assert sum(r.amount for r in overview.spending_by_category) == overview.spending_over_time.total


def test_annual_spending_by_category_lists_bills_and_subscriptions_with_shares_of_spending(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 1), amount=300.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 8, 2), amount=100.0, type="Bills & Subscriptions", category="Internet", notes="ISP"),
            make_transaction(date=date(2026, 8, 3), amount=875.0, type="Debt", category="Mortgage Repayment", notes="Werribee"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))

    assert overview.spending_by_category == [
        CategorySpend(category="Groceries", type="Expense", amount=300.0, pct_of_spending=75.0),
        CategorySpend(category="Internet", type="Bills & Subscriptions", amount=100.0, pct_of_spending=25.0),
    ]


def test_annual_overview_outflows_by_month_has_twelve_rows_with_unelapsed_months_zeroed(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 3), amount=100.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 7, 4), amount=60.0, type="Bills & Subscriptions", category="Phone Plan", notes="Telstra"),
            make_transaction(date=date(2026, 8, 5), amount=2000.0, type="Debt", category="Mortgage Repayment", notes="Loan"),
            make_transaction(date=date(2026, 9, 1), amount=999.0, type="Expense", category="Groceries", notes="Not yet elapsed"),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 21))
    rows = overview.outflows_by_month

    assert [(r.year, r.month) for r in rows][:3] == [(2026, 7), (2026, 8), (2026, 9)]
    assert len(rows) == 12
    assert (rows[0].expenses, rows[0].bills_subscriptions, rows[0].debt) == (100.0, 60.0, 0.0)
    assert (rows[1].expenses, rows[1].bills_subscriptions, rows[1].debt) == (0.0, 0.0, 2000.0)
    for unelapsed in rows[2:]:
        assert (unelapsed.expenses, unelapsed.bills_subscriptions, unelapsed.debt) == (0.0, 0.0, 0.0)


def test_annual_overview_outflows_by_month_leaves_savings_out_of_the_outflow_figures(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            make_transaction(date=date(2026, 7, 3), amount=100.0, type="Expense", category="Groceries", notes="Woolworths"),
            make_transaction(date=date(2026, 7, 4), amount=500.0, type="Savings", category="Savings", notes="Transfer"),
        ]
    )

    july = get_annual_overview(store, year=2026, today=date(2026, 8, 21)).outflows_by_month[0]

    assert (july.expenses, july.bills_subscriptions, july.debt) == (100.0, 0.0, 0.0)


def bs(make_transaction, when, amount, notes="Gym", category="Gym", id=1, type="Bills & Subscriptions"):
    return make_transaction(id=id, date=when, amount=amount, type=type, category=category, notes=notes)


def fortnightly_gym(make_transaction, first=date(2026, 5, 4), count=11, amount=37.5, id_start=100):
    return [
        bs(make_transaction, date.fromordinal(first.toordinal() + 14 * i), amount, id=id_start + i)
        for i in range(count)
    ]


def test_recurring_charges_project_a_fortnightly_charge_to_its_yearly_cost(fake_store, make_transaction):
    store = fake_store(transactions=fortnightly_gym(make_transaction))  # 11 x 37.50 = 412.50, 4 May - 21 Sep

    overview = get_month_overview(store, year=2026, month=9)

    (row,) = overview.recurring_charges.rows
    assert row.merchant == "Gym"
    assert row.category == "Gym"
    assert row.charges == 11
    assert row.last_charged == "2026-09-21"
    assert row.typical == 37.5
    assert row.cadence_days == 14
    assert row.per_year == 977.68  # 37.50 x 365 / 14, not the 412.50 paid so far


def test_recurring_charges_header_totals_are_per_year_and_a_twelfth_of_it(fake_store, make_transaction):
    store = fake_store(
        transactions=fortnightly_gym(make_transaction)
        + [bs(make_transaction, date(2026, 9, 1), 120.0, notes="Insurer", category="Insurance", id=1)]
    )

    charges = get_month_overview(store, year=2026, month=9).recurring_charges

    assert charges.per_year == 1097.68
    assert charges.per_month == 91.47
    assert [row.merchant for row in charges.rows] == ["Gym", "Insurer"]  # largest yearly cost first


def test_recurring_charges_single_charge_merchant_shows_what_was_paid_with_no_cadence(fake_store, make_transaction):
    store = fake_store(transactions=[bs(make_transaction, date(2026, 3, 10), 480.0, notes="Car Insurance", category="Insurance")])

    (row,) = get_month_overview(store, year=2026, month=9).recurring_charges.rows

    assert (row.charges, row.typical, row.cadence_days, row.per_year) == (1, 480.0, None, 480.0)


def test_recurring_charges_typical_is_the_median_and_slightly_varying_amounts_group_as_one_merchant(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            bs(make_transaction, date(2026, 6, 1), 60.0, notes="Telstra Mobile 1234", id=1),
            bs(make_transaction, date(2026, 7, 1), 64.0, notes="TELSTRA MOBILE 5678", id=2),
            bs(make_transaction, date(2026, 8, 1), 90.0, notes="Telstra Mobile 9", id=3),
        ]
    )

    (row,) = get_month_overview(store, year=2026, month=9).recurring_charges.rows

    assert row.merchant == "Telstra Mobile 9"
    assert row.charges == 3
    assert row.typical == 64.0
    assert row.cadence_days == 31  # gaps of 30 and 31 days: median 30.5 rounds half up to a whole day
    assert row.per_year == 753.55  # 64.00 x 365 / 31


def test_recurring_charges_window_is_the_twelve_months_ending_at_the_end_of_the_selected_month(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            bs(make_transaction, date(2025, 9, 30), 1.0, notes="Too early", id=1),
            bs(make_transaction, date(2025, 10, 1), 2.0, notes="First day in", id=2),
            bs(make_transaction, date(2026, 9, 30), 3.0, notes="Last day in", id=3),
            bs(make_transaction, date(2026, 10, 1), 4.0, notes="Too late", id=4),
        ]
    )

    rows = get_month_overview(store, year=2026, month=9).recurring_charges.rows

    assert sorted(row.merchant for row in rows) == ["First day in", "Last day in"]


def test_recurring_charges_only_cover_bills_and_subscriptions(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            bs(make_transaction, date(2026, 9, 1), 50.0, notes="Netflix", id=1),
            bs(make_transaction, date(2026, 9, 2), 20.0, notes="Cafe", category="Dining", type="Expense", id=2),
            bs(make_transaction, date(2026, 9, 3), 900.0, notes="Loan", category="Loan", type="Debt", id=3),
        ]
    )

    rows = get_month_overview(store, year=2026, month=9).recurring_charges.rows

    assert [row.merchant for row in rows] == ["Netflix"]


def test_recurring_charges_are_empty_when_there_are_no_bills_and_subscriptions(fake_store):
    charges = get_month_overview(fake_store(transactions=[]), year=2026, month=9).recurring_charges

    assert (charges.per_year, charges.per_month, charges.rows) == (0.0, 0.0, [])


def test_the_month_view_reads_earlier_months_for_recurring_charges_without_widening_its_other_figures(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            bs(make_transaction, date(2026, 8, 5), 30.0, notes="Streaming", id=1),
            bs(make_transaction, date(2026, 9, 5), 30.0, notes="Streaming", id=2),
        ]
    )

    overview = get_month_overview(store, year=2026, month=9)

    assert overview.stat_tiles.bills_subscriptions == 30.0
    assert [(m.merchant, m.total, m.count) for m in overview.top_merchants] == [("Streaming", 30.0, 1)]
    assert overview.recurring_charges.rows[0].charges == 2


def test_annual_recurring_charges_cover_the_twelve_months_ending_at_the_last_elapsed_month(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            bs(make_transaction, date(2025, 8, 31), 1.0, notes="Too early", id=1),
            bs(make_transaction, date(2025, 9, 1), 2.0, notes="Before the year", id=2),
            bs(make_transaction, date(2026, 8, 31), 3.0, notes="Last elapsed day", id=3),
            bs(make_transaction, date(2026, 9, 1), 4.0, notes="Not yet elapsed", id=4),
        ]
    )

    overview = get_annual_overview(store, year=2026, today=date(2026, 8, 15))

    assert sorted(row.merchant for row in overview.recurring_charges.rows) == ["Before the year", "Last elapsed day"]
    assert overview.stat_tiles.bills_subscriptions == 3.0


def test_annual_recurring_charges_are_empty_before_the_year_starts(fake_store, make_transaction):
    store = fake_store(transactions=[bs(make_transaction, date(2026, 3, 1), 5.0, id=1)])

    overview = get_annual_overview(store, year=2026, today=date(2026, 3, 1))

    assert overview.recurring_charges.rows == []


def spend(make_transaction, when, amount, category="Groceries", type="Expense", id=1):
    return make_transaction(id=id, date=when, amount=amount, type=type, category=category, notes=category)


def mover_rows(overview, basis):
    return {row.category: row for row in getattr(overview.movers, basis)}


def test_movers_carry_all_three_comparison_bases(fake_store, make_transaction):
    store = fake_store(transactions=[spend(make_transaction, date(2026, 9, 3), 10.0)])

    movers = get_month_overview(store, year=2026, month=9).movers

    assert [len(movers.previous_month), len(movers.avg_3_months), len(movers.avg_12_months)] == [1, 1, 1]


def test_movers_previous_month_compares_this_month_with_last_calendar_month(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            spend(make_transaction, date(2026, 7, 9), 500.0, id=1),
            spend(make_transaction, date(2026, 8, 9), 100.0, id=2),
            spend(make_transaction, date(2026, 9, 9), 150.0, id=3),
        ]
    )

    row = mover_rows(get_month_overview(store, year=2026, month=9), "previous_month")["Groceries"]

    assert (row.actual, row.comparison, row.diff, row.pct) == (150.0, 100.0, 50.0, 50.0)


def test_movers_three_month_comparison_is_the_sum_of_the_preceding_three_months_over_three_zeros_included(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            spend(make_transaction, date(2026, 5, 30), 999.0, id=1),  # outside the three months
            spend(make_transaction, date(2026, 6, 1), 90.0, id=2),
            spend(make_transaction, date(2026, 8, 31), 30.0, id=3),  # July had nothing: counts as 0
            spend(make_transaction, date(2026, 9, 1), 100.0, id=4),
        ]
    )

    row = mover_rows(get_month_overview(store, year=2026, month=9), "avg_3_months")["Groceries"]

    assert (row.actual, row.comparison, row.diff, row.pct) == (100.0, 40.0, 60.0, 150.0)


def test_movers_twelve_month_comparison_is_the_sum_of_the_preceding_twelve_months_over_twelve(
    fake_store, make_transaction
):
    store = fake_store(
        transactions=[
            spend(make_transaction, date(2025, 8, 31), 999.0, id=1),  # thirteen months back: outside
            spend(make_transaction, date(2025, 9, 1), 120.0, id=2),
            spend(make_transaction, date(2026, 8, 31), 240.0, id=3),
            spend(make_transaction, date(2026, 9, 1), 60.0, id=4),
        ]
    )

    row = mover_rows(get_month_overview(store, year=2026, month=9), "avg_12_months")["Groceries"]

    assert (row.actual, row.comparison, row.diff, row.pct) == (60.0, 30.0, 30.0, 100.0)


def test_movers_a_falling_category_has_a_negative_difference_and_percentage(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            spend(make_transaction, date(2026, 8, 9), 200.0, id=1),
            spend(make_transaction, date(2026, 9, 9), 150.0, id=2),
        ]
    )

    row = mover_rows(get_month_overview(store, year=2026, month=9), "previous_month")["Groceries"]

    assert (row.diff, row.pct) == (-50.0, -25.0)


def test_movers_a_category_new_this_month_has_no_percentage(fake_store, make_transaction):
    store = fake_store(transactions=[spend(make_transaction, date(2026, 9, 9), 80.0, category="Dining")])

    row = mover_rows(get_month_overview(store, year=2026, month=9), "avg_3_months")["Dining"]

    assert (row.actual, row.comparison, row.diff, row.pct) == (80.0, 0.0, 80.0, None)


def test_movers_a_category_that_stopped_this_month_falls_by_its_whole_comparison(fake_store, make_transaction):
    store = fake_store(transactions=[spend(make_transaction, date(2026, 8, 9), 80.0, category="Dining")])

    row = mover_rows(get_month_overview(store, year=2026, month=9), "previous_month")["Dining"]

    assert (row.actual, row.comparison, row.diff, row.pct) == (0.0, 80.0, -80.0, -100.0)


def test_movers_omit_a_category_with_no_activity_this_month_or_in_the_comparison_window(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            spend(make_transaction, date(2026, 5, 9), 80.0, category="Dining", id=1),  # before the 3-month window
            spend(make_transaction, date(2026, 9, 9), 10.0, id=2),
        ]
    )

    movers = get_month_overview(store, year=2026, month=9).movers

    assert [row.category for row in movers.previous_month] == ["Groceries"]
    assert [row.category for row in movers.avg_3_months] == ["Groceries"]
    assert sorted(row.category for row in movers.avg_12_months) == ["Dining", "Groceries"]


def test_movers_unchanged_category_is_kept_with_a_zero_difference(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            spend(make_transaction, date(2026, 8, 9), 70.0, id=1),
            spend(make_transaction, date(2026, 9, 9), 70.0, id=2),
        ]
    )

    row = mover_rows(get_month_overview(store, year=2026, month=9), "previous_month")["Groceries"]

    assert (row.diff, row.pct) == (0.0, 0.0)


def test_movers_are_sorted_by_absolute_difference_largest_first_then_by_name(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            spend(make_transaction, date(2026, 8, 1), 100.0, category="Falling", id=1),
            spend(make_transaction, date(2026, 9, 1), 60.0, category="Falling", id=2),  # -40
            spend(make_transaction, date(2026, 9, 2), 90.0, category="Rising", id=3),  # +90
            spend(make_transaction, date(2026, 9, 3), 40.0, category="Beta", id=4),  # +40
            spend(make_transaction, date(2026, 9, 4), 40.0, category="Alpha", id=5),  # +40
        ]
    )

    rows = get_month_overview(store, year=2026, month=9).movers.previous_month

    assert [row.category for row in rows] == ["Rising", "Alpha", "Beta", "Falling"]


def test_movers_cover_spending_categories_only(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            spend(make_transaction, date(2026, 9, 1), 10.0, category="Groceries", id=1),
            spend(make_transaction, date(2026, 9, 2), 20.0, category="Gym", type="Bills & Subscriptions", id=2),
            spend(make_transaction, date(2026, 9, 3), 900.0, category="Loan", type="Debt", id=3),
            spend(make_transaction, date(2026, 9, 4), 500.0, category="Savings", type="Savings", id=4),
            spend(make_transaction, date(2026, 9, 5), 3000.0, category="Salary", type="Income", id=5),
        ]
    )

    rows = get_month_overview(store, year=2026, month=9).movers.previous_month

    assert sorted(row.category for row in rows) == ["Groceries", "Gym"]


def test_movers_are_empty_for_a_month_with_no_spending(fake_store):
    movers = get_month_overview(fake_store(transactions=[]), year=2026, month=9).movers

    assert (movers.previous_month, movers.avg_3_months, movers.avg_12_months) == ([], [], [])


def test_movers_look_back_across_a_year_boundary(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            spend(make_transaction, date(2025, 12, 20), 100.0, id=1),
            spend(make_transaction, date(2026, 1, 20), 130.0, id=2),
        ]
    )

    row = mover_rows(get_month_overview(store, year=2026, month=1), "previous_month")["Groceries"]

    assert (row.comparison, row.diff) == (100.0, 30.0)


def test_widening_the_month_read_for_movers_leaves_recurring_charges_at_twelve_months(fake_store, make_transaction):
    store = fake_store(
        transactions=[
            bs(make_transaction, date(2025, 9, 30), 1.0, notes="Just before the window", id=1),
            bs(make_transaction, date(2025, 10, 1), 2.0, notes="First day in the window", id=2),
        ]
    )

    overview = get_month_overview(store, year=2026, month=9)

    assert [row.merchant for row in overview.recurring_charges.rows] == ["First day in the window"]
    assert overview.stat_tiles.bills_subscriptions == 0.0


def test_the_full_year_overview_has_no_movers(fake_store):
    overview = get_annual_overview(fake_store(transactions=[]), year=2026, today=date(2026, 8, 15))

    assert not hasattr(overview, "movers")
