from datetime import date

import pytest

from categorisation.interface import BatchResult, CategoryResult
from statement_export.parser import RawTransaction
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

    def categorise(self, transactions: list[RawTransaction], category_list: dict[str, set[str]]) -> BatchResult:
        self.calls.append(transactions)
        if self._error is not None:
            raise self._error
        return BatchResult(results=self._results)


class FakeSheetsClient:
    """In-memory stand-in for the Transaction Log's Google Sheets client.

    Used wherever a test needs Transaction Log reads/writes without live
    Sheets access — GoogleSheetsClient (transaction_log.sheets_client) is the
    real counterpart.
    """

    def __init__(self, existing_rows: list[ExistingRow] | None = None):
        self._existing_rows = list(existing_rows or [])
        self.appended: list[Candidate] = []

    def read_existing_rows(self) -> list[ExistingRow]:
        return list(self._existing_rows)

    def append_rows(self, candidates: list[Candidate]) -> None:
        self.appended.extend(candidates)


@pytest.fixture
def make_candidate():
    def _make_candidate(**overrides):
        defaults = dict(
            date=date(2026, 8, 5),
            amount=42.50,
            category="Expenses",
            sub_category="Groceries",
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
def fake_sheets_client():
    return FakeSheetsClient


@pytest.fixture
def make_category_result():
    def _make_category_result(**overrides):
        defaults = dict(category="Expenses", sub_category="Groceries", needs_review=False, reason=None)
        defaults.update(overrides)
        return CategoryResult(**defaults)

    return _make_category_result


@pytest.fixture
def fake_categoriser():
    return FakeCategoriser
