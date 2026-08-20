from datetime import date

import pytest

from categorisation.interface import BatchResult, CategoryResult
from recurring.rules import RecurringRule
from statement_export.parser import RawTransaction
from transaction_log.categories import is_valid_type_category_pair
from transaction_log.entries import Candidate, ExistingRow


class FakeCategoriser:
    """In-memory stand-in for a Categoriser backend.

    Returns canned CategoryResults (in order) or raises a canned error -
    used wherever a test needs categorisation without a real subprocess or
    network call. The concrete backends (categorisation.claude_backend etc.)
    are the real counterparts.
    """

    def __init__(self, results: list[CategoryResult] | None = None, error: Exception | None = None):
        self._results = results
        self._error = error
        self.calls: list[list[RawTransaction]] = []

    def categorise(self, transactions: list[RawTransaction], categories_by_type: dict[str, set[str]]) -> BatchResult:
        self.calls.append(transactions)
        if self._error is not None:
            raise self._error
        return BatchResult(results=self._results)


class FakeStore:
    """In-memory stand-in for the local database store.

    Used wherever a test needs Transaction Log/Recurring Transactions Config
    reads or writes without a real SQLite database — LocalStore
    (database.store) is the real counterpart.
    """

    def __init__(
        self,
        existing_rows: list[ExistingRow] | None = None,
        recurring_rules: list[RecurringRule] | None = None,
        category_budgets: dict[str, float] | None = None,
    ):
        self._existing_rows = list(existing_rows or [])
        self._recurring_rules = list(recurring_rules or [])
        self._category_budgets: dict[str, float] = dict(category_budgets or {})
        self.appended: list[Candidate] = []

    def read_existing_rows(self) -> list[ExistingRow]:
        return list(self._existing_rows)

    def append_rows(self, candidates: list[Candidate]) -> None:
        self.appended.extend(candidates)

    def read_recurring_rules(self) -> list[RecurringRule]:
        return list(self._recurring_rules)

    def append_recurring_rules(self, rules: list[RecurringRule]) -> None:
        self._recurring_rules.extend(rules)

    def read_category_budgets(self) -> dict[str, float]:
        return dict(self._category_budgets)

    def upsert_category_budget(self, category: str, monthly_amount: float) -> None:
        if not is_valid_type_category_pair("Expense", category):
            raise ValueError(f"Category {category!r} is not a valid Expense Category")
        self._category_budgets[category] = monthly_amount

    def delete_category_budget(self, category: str) -> None:
        self._category_budgets.pop(category, None)


@pytest.fixture
def make_candidate():
    def _make_candidate(**overrides):
        defaults = dict(
            date=date(2026, 8, 5),
            amount=42.50,
            type="Expense",
            category="Groceries",
            notes="Woolworths",
        )
        defaults.update(overrides)
        return Candidate(**defaults)

    return _make_candidate


@pytest.fixture
def make_existing_row():
    def _make_existing_row(**overrides):
        defaults = dict(
            date=date(2026, 8, 5),
            amount=42.50,
            notes="Woolworths",
        )
        defaults.update(overrides)
        return ExistingRow(**defaults)

    return _make_existing_row


@pytest.fixture
def fake_store():
    return FakeStore


@pytest.fixture
def make_rule():
    def _make_rule(**overrides):
        defaults = dict(
            amount=100.0,
            type="Expense",
            category="Subscriptions",
            notes="Test rule",
            frequency="Weekly",
            interval=1,
            day="Wednesday",
            start_date=date(2026, 8, 5),  # a Wednesday
            end_date=None,
        )
        defaults.update(overrides)
        return RecurringRule(**defaults)

    return _make_rule


@pytest.fixture
def make_category_result():
    def _make_category_result(**overrides):
        defaults = dict(type="Expense", category="Groceries", needs_review=False, reason=None)
        defaults.update(overrides)
        return CategoryResult(**defaults)

    return _make_category_result


@pytest.fixture
def fake_categoriser():
    return FakeCategoriser
