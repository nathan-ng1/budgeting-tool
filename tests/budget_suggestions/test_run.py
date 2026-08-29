from datetime import date, datetime

import pytest

from advisor.interface import CategoryHistory, SuggestionResult
from budget_suggestions.run import generate_budget_suggestion


class FakeAdvisor:
    def __init__(self, write_up: str = "Groceries is trending over budget.", error: Exception | None = None):
        self._write_up = write_up
        self._error = error
        self.calls: list[list[CategoryHistory]] = []

    def advise(self, history: list[CategoryHistory]) -> SuggestionResult:
        self.calls.append(history)
        if self._error is not None:
            raise self._error
        return SuggestionResult(write_up=self._write_up)


def test_passes_expense_and_debt_history_but_excludes_income_and_savings(fake_store, make_transaction):
    # Issue #136 - Category Budget now covers Savings too, but the Budget
    # Suggestion write-up stays scoped to Expense/Debt, unchanged.
    store = fake_store(
        transactions=[
            make_transaction(id=1, date=date(2026, 7, 5), type="Expense", category="Groceries", amount=450.0),
            make_transaction(id=2, date=date(2026, 7, 6), type="Debt", category="Mortgage Repayment", amount=2000.0),
            make_transaction(id=3, date=date(2026, 7, 7), type="Income", category="Salary", amount=5000.0),
            make_transaction(id=4, date=date(2026, 7, 8), type="Savings", category="Savings", amount=600.0),
        ]
    )
    advisor = FakeAdvisor()

    generate_budget_suggestion(store, advisor, today=date(2026, 8, 24))

    [history] = advisor.calls
    types = {row.type for row in history}
    assert types == {"Expense", "Debt"}
    assert "Income" not in types
    assert "Savings" not in types


def test_stores_the_write_up_as_the_standing_budget_suggestion(fake_store):
    store = fake_store()
    advisor = FakeAdvisor(write_up="Groceries is trending over budget.")

    generate_budget_suggestion(store, advisor, today=date(2026, 8, 24))

    assert store.read_budget_suggestion().write_up == "Groceries is trending over budget."


def test_regenerating_replaces_the_previous_write_up_outright(fake_store):
    store = fake_store()
    store.write_budget_suggestion("Stale write-up.", datetime(2026, 7, 1))

    generate_budget_suggestion(store, FakeAdvisor(write_up="Fresh write-up."), today=date(2026, 8, 24))

    assert store.read_budget_suggestion().write_up == "Fresh write-up."


def test_returns_the_write_up(fake_store):
    store = fake_store()

    result = generate_budget_suggestion(store, FakeAdvisor(write_up="Groceries is trending over budget."), today=date(2026, 8, 24))

    assert result == "Groceries is trending over budget."


def test_an_erroring_advisor_propagates_and_writes_nothing(fake_store):
    store = fake_store()
    advisor = FakeAdvisor(error=RuntimeError("backend exploded"))

    with pytest.raises(RuntimeError, match="backend exploded"):
        generate_budget_suggestion(store, advisor, today=date(2026, 8, 24))

    assert store.read_budget_suggestion() is None
