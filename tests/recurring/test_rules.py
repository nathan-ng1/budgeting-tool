from datetime import date

import pytest

from recurring.rules import RecurringRule


def _rule(**overrides):
    defaults = dict(
        amount=100.0,
        category="Bills & Subscriptions",
        sub_category="Subscriptions",
        notes="Test rule",
        frequency="Weekly",
        interval=1,
        day="Wednesday",
        start_date=date(2026, 8, 5),  # a Wednesday
        end_date=None,
    )
    defaults.update(overrides)
    return RecurringRule(**defaults)


def test_weekly_start_date_must_fall_on_the_configured_weekday():
    with pytest.raises(ValueError):
        _rule(frequency="Weekly", day="Monday", start_date=date(2026, 8, 5))  # a Wednesday


def test_monthly_day_must_be_between_1_and_31():
    with pytest.raises(ValueError):
        _rule(frequency="Monthly", day=32, start_date=date(2026, 8, 5))


def test_end_date_before_start_date_is_rejected():
    with pytest.raises(ValueError):
        _rule(start_date=date(2026, 8, 5), end_date=date(2026, 8, 1))
