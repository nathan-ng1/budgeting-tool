from datetime import date, datetime

import pytest

from budget_suggestions.suggestion import BudgetSuggestion
from categorisation.interface import BatchResult, CategoryResult
from database.store import RecurringRuleNotFound, TransactionNotFound
from recurring.rules import RecurringRule, StoredRecurringRule
from statement_export.parser import RawTransaction
from transaction_log.categories import CATEGORIES_BY_TYPE, Category, require_valid_type_category_pair
from transaction_log.entries import Candidate, ExistingRow, Transaction

# FakeStore.read_categories()'s default - mirrors database.store's own
# _seed_default_categories bootstrap (Beem Adjustment locked), so a test using
# FakeStore sees the same Category list a fresh LocalStore would.
_DEFAULT_CATEGORIES = [
    Category(id=i, type=transaction_type, name=name, emoji=None, locked=(name == "Beem Adjustment"))
    for i, (transaction_type, name) in enumerate(
        (
            (transaction_type, name)
            for transaction_type, names in CATEGORIES_BY_TYPE.items()
            for name in sorted(names)
        ),
        start=1,
    )
]


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

    def categorise(self, transactions: list[RawTransaction], categories: list[Category]) -> BatchResult:
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
        category_budgets: dict[tuple[str, int, int], float] | None = None,
        transactions: list[Transaction] | None = None,
        budget_suggestion: BudgetSuggestion | None = None,
    ):
        self._existing_rows = list(existing_rows or [])
        self._recurring_rules = list(recurring_rules or [])
        # Keyed by (category, year, month), mirroring LocalStore's composite key.
        self._category_budgets: dict[tuple[str, int, int], float] = dict(category_budgets or {})
        self._transactions = list(transactions or [])
        self._budget_suggestion = budget_suggestion
        self._stored_recurring_rules: list[StoredRecurringRule] = []
        self._next_rule_id = 0
        self._next_transaction_id = max((t.id for t in self._transactions), default=0)
        self.appended: list[Candidate] = []

    def read_existing_rows(self) -> list[ExistingRow]:
        return list(self._existing_rows)

    def read_transactions(self) -> list[Transaction]:
        return list(self._transactions)

    def append_rows(self, candidates: list[Candidate]) -> None:
        self.appended.extend(candidates)

    def create_transaction(self, candidate: Candidate) -> Transaction:
        self._next_transaction_id += 1
        created = Transaction(
            id=self._next_transaction_id,
            date=candidate.date,
            amount=candidate.amount,
            type=candidate.type,
            category=candidate.category,
            notes=candidate.notes,
        )
        self._transactions.append(created)
        return created

    def update_transaction(self, transaction_id: int, candidate: Candidate) -> Transaction:
        index = self._transaction_index(transaction_id)
        updated = Transaction(
            id=transaction_id,
            date=candidate.date,
            amount=candidate.amount,
            type=candidate.type,
            category=candidate.category,
            notes=candidate.notes,
        )
        self._transactions[index] = updated
        return updated

    def delete_transaction(self, transaction_id: int) -> None:
        del self._transactions[self._transaction_index(transaction_id)]

    def _transaction_index(self, transaction_id: int) -> int:
        for index, transaction in enumerate(self._transactions):
            if transaction.id == transaction_id:
                return index
        raise TransactionNotFound(f"No Transaction has id {transaction_id}")

    def read_recurring_rules(self) -> list[RecurringRule]:
        # One table behind both read paths, as in LocalStore: a rule created
        # through the Dashboard is expanded on the next Statement Export run.
        return [*self._recurring_rules, *(stored.rule for stored in self._stored_recurring_rules)]

    def append_recurring_rules(self, rules: list[RecurringRule]) -> None:
        self._recurring_rules.extend(rules)

    def read_stored_recurring_rules(self) -> list[StoredRecurringRule]:
        return list(self._stored_recurring_rules)

    def create_recurring_rule(self, rule: RecurringRule) -> StoredRecurringRule:
        self._validate_pair(rule)
        self._next_rule_id += 1
        stored = StoredRecurringRule(id=self._next_rule_id, rule=rule)
        self._stored_recurring_rules.append(stored)
        return stored

    def update_recurring_rule(self, rule_id: int, rule: RecurringRule) -> StoredRecurringRule:
        self._validate_pair(rule)
        index = self._index_of(rule_id)
        updated = StoredRecurringRule(id=rule_id, rule=rule)
        self._stored_recurring_rules[index] = updated
        return updated

    def delete_recurring_rule(self, rule_id: int) -> None:
        del self._stored_recurring_rules[self._index_of(rule_id)]

    def _index_of(self, rule_id: int) -> int:
        for index, stored in enumerate(self._stored_recurring_rules):
            if stored.id == rule_id:
                return index
        raise RecurringRuleNotFound(f"No Recurring Transactions Config rule has id {rule_id}")

    @staticmethod
    def _validate_pair(rule: RecurringRule) -> None:
        require_valid_type_category_pair(rule.type, rule.category)

    def read_category_budgets(self, year: int, month: int) -> dict[str, float]:
        return {
            category: amount
            for (category, budget_year, budget_month), amount in self._category_budgets.items()
            if budget_year == year and budget_month == month
        }

    def read_category_budgets_for_range(
        self, category: str, start_year: int, start_month: int, end_year: int, end_month: int
    ) -> dict[tuple[int, int], float]:
        start_index = start_year * 12 + start_month
        end_index = end_year * 12 + end_month
        return {
            (budget_year, budget_month): amount
            for (budget_category, budget_year, budget_month), amount in self._category_budgets.items()
            if budget_category == category and start_index <= budget_year * 12 + budget_month <= end_index
        }

    def upsert_category_budget(
        self, transaction_type: str, category: str, year: int, month: int, amount: float
    ) -> None:
        require_valid_type_category_pair(transaction_type, category)
        self._category_budgets[(category, year, month)] = amount

    def delete_category_budget(self, category: str, year: int, month: int) -> None:
        self._category_budgets.pop((category, year, month), None)

    def write_budget_suggestion(self, write_up: str, generated_at: datetime) -> None:
        self._budget_suggestion = BudgetSuggestion(write_up=write_up, generated_at=generated_at)

    def read_budget_suggestion(self) -> BudgetSuggestion | None:
        return self._budget_suggestion

    def read_categories(self) -> list[Category]:
        return list(_DEFAULT_CATEGORIES)


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
def make_transaction():
    def _make_transaction(**overrides):
        defaults = dict(
            id=1,
            date=date(2026, 8, 5),
            amount=42.50,
            type="Expense",
            category="Groceries",
            notes="Woolworths",
        )
        defaults.update(overrides)
        return Transaction(**defaults)

    return _make_transaction


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
