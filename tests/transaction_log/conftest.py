from datetime import date

import pytest

from transaction_log.entries import Candidate, ExistingRow


class FakeSheetsClient:
    """In-memory stand-in for the Transaction Log's Google Sheets client.

    Issue #5 requires no live Sheets access; this is what tests read existing
    Transaction Log rows from instead. Issue #6 swaps in the real client.
    """

    def __init__(self, existing_rows: list[ExistingRow] | None = None):
        self._existing_rows = list(existing_rows or [])

    def read_existing_rows(self) -> list[ExistingRow]:
        return list(self._existing_rows)


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
