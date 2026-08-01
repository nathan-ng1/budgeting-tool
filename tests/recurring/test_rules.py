from datetime import date

import pytest


def test_weekly_start_date_must_fall_on_the_configured_weekday(make_rule):
    with pytest.raises(ValueError):
        make_rule(frequency="Weekly", day="Monday", start_date=date(2026, 8, 5))  # a Wednesday


def test_monthly_day_must_be_between_1_and_31(make_rule):
    with pytest.raises(ValueError):
        make_rule(frequency="Monthly", day=32, start_date=date(2026, 8, 5))


def test_monthly_start_date_day_must_match_configured_day(make_rule):
    with pytest.raises(ValueError):
        make_rule(frequency="Monthly", day=15, start_date=date(2026, 8, 10))


def test_monthly_start_date_day_may_match_the_clamped_day_for_a_shorter_month(make_rule):
    # Day=31 clamps to Feb 28 in 2026 (not a leap year), so starting on Feb 28 is valid.
    make_rule(frequency="Monthly", day=31, start_date=date(2026, 2, 28))


def test_end_date_before_start_date_is_rejected(make_rule):
    with pytest.raises(ValueError):
        make_rule(start_date=date(2026, 8, 5), end_date=date(2026, 8, 1))
