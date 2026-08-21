import sqlite3
from datetime import date
from pathlib import Path

import pytest

from database.store import RecurringRuleNotFound, connect
from recurring.rules import RecurringRule
from transaction_log.entries import ExistingRow, Transaction


def test_read_existing_rows_on_a_fresh_database_returns_no_rows(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    assert store.read_existing_rows() == []


def test_append_rows_then_read_existing_rows_round_trips(tmp_path: Path, make_candidate):
    store = connect(tmp_path / "budget.db")
    candidate = make_candidate(date=date(2026, 8, 5), amount=42.5, notes="Woolworths")

    store.append_rows([candidate])

    assert store.read_existing_rows() == [
        ExistingRow(date=date(2026, 8, 5), amount=42.5, notes="Woolworths")
    ]


def test_append_rows_writes_a_negative_source_amount_as_positive(tmp_path: Path, make_candidate):
    store = connect(tmp_path / "budget.db")
    candidate = make_candidate(amount=-42.50, notes="Woolworths")

    store.append_rows([candidate])

    [row] = store.read_existing_rows()
    assert row.amount == 42.50


def test_append_rows_with_no_candidates_is_a_noop(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    store.append_rows([])

    assert store.read_existing_rows() == []


def test_append_rows_persists_across_reconnects(tmp_path: Path, make_candidate):
    database_path = tmp_path / "budget.db"
    connect(database_path).append_rows([make_candidate(notes="Woolworths")])

    reopened = connect(database_path)

    assert [row.notes for row in reopened.read_existing_rows()] == ["Woolworths"]


def test_read_transactions_on_a_fresh_database_returns_no_transactions(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    assert store.read_transactions() == []


def test_append_rows_then_read_transactions_round_trips_type_and_category(tmp_path: Path, make_candidate):
    store = connect(tmp_path / "budget.db")
    candidate = make_candidate(date=date(2026, 8, 5), amount=42.5, type="Expense", category="Groceries", notes="Woolworths")

    store.append_rows([candidate])

    assert store.read_transactions() == [
        Transaction(date=date(2026, 8, 5), amount=42.5, type="Expense", category="Groceries", notes="Woolworths")
    ]


def test_read_recurring_rules_on_a_fresh_database_returns_no_rules(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    assert store.read_recurring_rules() == []


def test_read_recurring_rules_round_trips_a_monthly_rule(tmp_path: Path):
    database_path = tmp_path / "budget.db"
    store = connect(database_path)
    _insert_recurring_rule(
        database_path,
        amount=4200.0,
        type="Income",
        category="Salary",
        notes="Employer Pty Ltd",
        frequency="Monthly",
        interval=1,
        day="15",
        start_date="2026-01-15",
        end_date=None,
    )

    assert store.read_recurring_rules() == [
        RecurringRule(
            amount=4200.0,
            type="Income",
            category="Salary",
            notes="Employer Pty Ltd",
            frequency="Monthly",
            interval=1,
            day=15,
            start_date=date(2026, 1, 15),
            end_date=None,
        )
    ]


def test_read_recurring_rules_round_trips_a_weekly_rule_with_an_end_date(tmp_path: Path):
    database_path = tmp_path / "budget.db"
    store = connect(database_path)
    _insert_recurring_rule(
        database_path,
        amount=100.0,
        type="Expense",
        category="Subscriptions",
        notes="Streaming service",
        frequency="Weekly",
        interval=2,
        day="Wednesday",
        start_date="2026-08-05",
        end_date="2026-12-31",
    )

    [rule] = store.read_recurring_rules()

    assert rule.day == "Wednesday"
    assert rule.interval == 2
    assert rule.end_date == date(2026, 12, 31)


def test_append_recurring_rules_then_read_recurring_rules_round_trips(tmp_path: Path, make_rule):
    store = connect(tmp_path / "budget.db")
    rule = make_rule(notes="Employer Pty Ltd")

    store.append_recurring_rules([rule])

    assert store.read_recurring_rules() == [rule]


def test_append_recurring_rules_with_no_rules_is_a_noop(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    store.append_recurring_rules([])

    assert store.read_recurring_rules() == []


def test_read_category_budgets_on_a_fresh_database_returns_no_budgets(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    assert store.read_category_budgets() == {}


def test_upsert_category_budget_then_read_category_budgets_round_trips(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    store.upsert_category_budget("Groceries", 500.0)

    assert store.read_category_budgets() == {"Groceries": 500.0}


def test_read_category_budgets_omits_categories_with_none_configured(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    store.upsert_category_budget("Groceries", 500.0)

    assert "Dining & Takeaway" not in store.read_category_budgets()


def test_upsert_category_budget_overwrites_an_existing_budget(tmp_path: Path):
    store = connect(tmp_path / "budget.db")
    store.upsert_category_budget("Groceries", 500.0)

    store.upsert_category_budget("Groceries", 600.0)

    assert store.read_category_budgets() == {"Groceries": 600.0}


def test_upsert_category_budget_rejects_a_category_not_in_the_expense_set(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    with pytest.raises(ValueError):
        store.upsert_category_budget("Salary", 500.0)

    assert store.read_category_budgets() == {}


def test_upsert_category_budget_rejects_an_unknown_category(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    with pytest.raises(ValueError):
        store.upsert_category_budget("Not A Real Category", 500.0)


def test_delete_category_budget_removes_it_so_it_no_longer_appears(tmp_path: Path):
    store = connect(tmp_path / "budget.db")
    store.upsert_category_budget("Groceries", 500.0)

    store.delete_category_budget("Groceries")

    assert store.read_category_budgets() == {}


def test_delete_category_budget_for_a_category_with_no_budget_is_a_noop(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    store.delete_category_budget("Groceries")

    assert store.read_category_budgets() == {}


def _insert_recurring_rule(database_path: Path, **fields) -> None:
    connection = sqlite3.connect(database_path)
    connection.execute(
        "INSERT INTO recurring_rules "
        "(amount, type, category, notes, frequency, interval, day, start_date, end_date) "
        "VALUES (:amount, :type, :category, :notes, :frequency, :interval, :day, :start_date, :end_date)",
        fields,
    )
    connection.commit()
    connection.close()


def test_read_stored_recurring_rules_on_a_fresh_database_returns_no_rules(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    assert store.read_stored_recurring_rules() == []


def test_create_recurring_rule_returns_the_rule_with_the_id_it_was_given(tmp_path: Path, make_rule):
    store = connect(tmp_path / "budget.db")
    rule = make_rule(notes="Streaming service")

    stored = store.create_recurring_rule(rule)

    assert stored.rule == rule
    assert stored.id is not None
    assert store.read_stored_recurring_rules() == [stored]


def test_create_recurring_rule_gives_each_rule_its_own_id(tmp_path: Path, make_rule):
    store = connect(tmp_path / "budget.db")

    first = store.create_recurring_rule(make_rule(notes="First"))
    second = store.create_recurring_rule(make_rule(notes="Second"))

    assert first.id != second.id


def test_a_rule_created_through_the_dashboard_is_visible_to_the_expansion_path(tmp_path: Path, make_rule):
    store = connect(tmp_path / "budget.db")
    rule = make_rule(notes="Streaming service")

    store.create_recurring_rule(rule)

    assert store.read_recurring_rules() == [rule]


def test_create_recurring_rule_rejects_an_invalid_type_category_pair(tmp_path: Path, make_rule):
    store = connect(tmp_path / "budget.db")

    with pytest.raises(ValueError, match="Salary"):
        store.create_recurring_rule(make_rule(type="Expense", category="Salary"))

    assert store.read_stored_recurring_rules() == []


def test_create_recurring_rule_rejects_an_unknown_category(tmp_path: Path, make_rule):
    store = connect(tmp_path / "budget.db")

    with pytest.raises(ValueError):
        store.create_recurring_rule(make_rule(category="Not A Real Category"))


def test_update_recurring_rule_replaces_the_rule_and_keeps_its_id(tmp_path: Path, make_rule):
    store = connect(tmp_path / "budget.db")
    stored = store.create_recurring_rule(make_rule(amount=100.0, notes="Streaming service"))
    replacement = make_rule(amount=150.0, notes="Streaming service, dearer now")

    updated = store.update_recurring_rule(stored.id, replacement)

    assert updated.id == stored.id
    assert updated.rule == replacement
    assert store.read_stored_recurring_rules() == [updated]


def test_update_recurring_rule_changes_what_the_expansion_path_reads(tmp_path: Path, make_rule):
    store = connect(tmp_path / "budget.db")
    stored = store.create_recurring_rule(make_rule(amount=100.0))

    store.update_recurring_rule(stored.id, make_rule(amount=150.0))

    assert [rule.amount for rule in store.read_recurring_rules()] == [150.0]


def test_update_recurring_rule_leaves_the_rule_alone_when_the_replacement_is_invalid(tmp_path: Path, make_rule):
    store = connect(tmp_path / "budget.db")
    original = make_rule(category="Subscriptions")
    stored = store.create_recurring_rule(original)

    with pytest.raises(ValueError):
        store.update_recurring_rule(stored.id, make_rule(type="Expense", category="Salary"))

    assert store.read_stored_recurring_rules() == [stored]


def test_update_recurring_rule_on_an_unknown_id_raises(tmp_path: Path, make_rule):
    store = connect(tmp_path / "budget.db")

    with pytest.raises(RecurringRuleNotFound):
        store.update_recurring_rule(404, make_rule())


def test_delete_recurring_rule_removes_it_from_both_read_paths(tmp_path: Path, make_rule):
    store = connect(tmp_path / "budget.db")
    stored = store.create_recurring_rule(make_rule())

    store.delete_recurring_rule(stored.id)

    assert store.read_stored_recurring_rules() == []
    assert store.read_recurring_rules() == []


def test_delete_recurring_rule_leaves_the_other_rules_alone(tmp_path: Path, make_rule):
    store = connect(tmp_path / "budget.db")
    doomed = store.create_recurring_rule(make_rule(notes="Doomed"))
    survivor = store.create_recurring_rule(make_rule(notes="Survivor"))

    store.delete_recurring_rule(doomed.id)

    assert store.read_stored_recurring_rules() == [survivor]


def test_delete_recurring_rule_on_an_unknown_id_raises(tmp_path: Path):
    store = connect(tmp_path / "budget.db")

    with pytest.raises(RecurringRuleNotFound):
        store.delete_recurring_rule(404)


def test_stored_recurring_rules_round_trip_a_monthly_rule_with_an_end_date(tmp_path: Path, make_rule):
    store = connect(tmp_path / "budget.db")
    rule = make_rule(
        type="Income",
        category="Salary",
        frequency="Monthly",
        interval=1,
        day=15,
        start_date=date(2026, 1, 15),
        end_date=date(2026, 12, 31),
    )

    stored = store.create_recurring_rule(rule)

    assert store.read_stored_recurring_rules() == [stored]
    assert store.read_stored_recurring_rules()[0].rule.day == 15
