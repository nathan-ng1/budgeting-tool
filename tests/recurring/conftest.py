from datetime import date

import pytest

from recurring.rules import RecurringRule


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
