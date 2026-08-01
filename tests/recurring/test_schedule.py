from datetime import date

from recurring.rules import RecurringRule
from recurring.schedule import expand


def _rule(**overrides):
    defaults = dict(
        amount=100.0,
        category="Bills & Subscriptions",
        sub_category="Subscriptions",
        notes="Test rule",
        frequency="Weekly",
        interval=1,
        day="Wednesday",
        start_date=date(2026, 8, 5),
        end_date=None,
    )
    defaults.update(overrides)
    return RecurringRule(**defaults)


def test_weekly_fortnightly_produces_correct_cadence():
    rule = _rule(frequency="Weekly", interval=2, day="Wednesday", start_date=date(2026, 8, 5))

    occurrences = expand(rule, through=date(2026, 9, 15))

    assert [o.date for o in occurrences] == [
        date(2026, 8, 5),
        date(2026, 8, 19),
        date(2026, 9, 2),
    ]


def test_monthly_produces_one_occurrence_per_interval_month_on_given_day():
    rule = _rule(frequency="Monthly", interval=1, day=15, start_date=date(2026, 1, 15))

    occurrences = expand(rule, through=date(2026, 4, 15))

    assert [o.date for o in occurrences] == [
        date(2026, 1, 15),
        date(2026, 2, 15),
        date(2026, 3, 15),
        date(2026, 4, 15),
    ]


def test_monthly_clamps_day_to_last_day_of_shorter_month():
    rule = _rule(frequency="Monthly", interval=1, day=31, start_date=date(2026, 1, 31))

    occurrences = expand(rule, through=date(2026, 3, 31))

    assert [o.date for o in occurrences] == [
        date(2026, 1, 31),
        date(2026, 2, 28),  # 2026 is not a leap year
        date(2026, 3, 31),
    ]


def test_end_date_stops_future_occurrences():
    rule = _rule(
        frequency="Monthly",
        interval=1,
        day=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 1),
    )

    occurrences = expand(rule, through=date(2026, 12, 31))

    assert [o.date for o in occurrences] == [
        date(2026, 1, 1),
        date(2026, 2, 1),
        date(2026, 3, 1),
    ]


def test_no_end_date_keeps_producing_occurrences_up_to_through_date():
    rule = _rule(
        frequency="Monthly",
        interval=3,
        day=1,
        start_date=date(2026, 1, 1),
        end_date=None,
    )

    occurrences = expand(rule, through=date(2027, 1, 1))

    assert [o.date for o in occurrences] == [
        date(2026, 1, 1),
        date(2026, 4, 1),
        date(2026, 7, 1),
        date(2026, 10, 1),
        date(2027, 1, 1),
    ]
