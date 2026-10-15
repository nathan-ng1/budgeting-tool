"""The figures derived from a Goal (Goals spec section 7): Status, months,
required per month, Original plan and pace. Pure calendar and money maths, so
these run without a Database; the endpoint test covers them over HTTP."""

from datetime import date

import pytest

from goals.figures import describe, months_inclusive
from goals.goal import ACTIVE, Goal


def goal(target=1200.0, start=date(2026, 1, 1), end=date(2026, 12, 31)) -> Goal:
    return Goal(
        id=1,
        title="Trip",
        description=None,
        target_amount=target,
        start_date=start,
        end_date=end,
        state=ACTIVE,
    )


# --- months: inclusive calendar months, minimum one ---


def test_months_count_both_end_months():
    assert months_inclusive(date(2026, 10, 14), date(2026, 12, 15)) == 3


def test_months_within_one_calendar_month_is_one():
    assert months_inclusive(date(2026, 10, 1), date(2026, 10, 31)) == 1


def test_months_across_a_year_boundary():
    assert months_inclusive(date(2026, 11, 30), date(2027, 2, 1)) == 4


def test_months_never_drop_below_one_when_the_dates_are_reversed():
    assert months_inclusive(date(2026, 12, 1), date(2026, 10, 1)) == 1


# --- Status, in precedence: Achieved, Ended, Upcoming, Active ---


def test_active_between_start_and_end():
    figures = describe(goal(), saved=0.0, today=date(2026, 6, 15))

    assert figures.status == "Active"


def test_upcoming_before_the_start_date():
    figures = describe(goal(start=date(2026, 7, 1)), saved=0.0, today=date(2026, 6, 15))

    assert figures.status == "Upcoming"
    assert figures.flag == "Upcoming"


def test_ended_after_the_end_date_when_not_fully_saved():
    figures = describe(goal(), saved=500.0, today=date(2027, 1, 1))

    assert figures.status == "Ended"
    assert figures.flag == "Ended"


def test_the_end_date_itself_is_still_active():
    figures = describe(goal(), saved=0.0, today=date(2026, 12, 31))

    assert figures.status == "Active"


def test_achieved_when_saved_reaches_the_target():
    figures = describe(goal(target=1000.0), saved=1000.0, today=date(2026, 6, 15))

    assert figures.status == "Achieved"
    assert figures.flag == "Achieved"


def test_achieved_beats_ended():
    figures = describe(goal(target=1000.0), saved=1200.0, today=date(2027, 6, 1))

    assert figures.status == "Achieved"
    assert figures.over == 200.0


def test_achieved_beats_upcoming():
    figures = describe(goal(target=1000.0, start=date(2026, 7, 1)), saved=1000.0, today=date(2026, 6, 15))

    assert figures.status == "Achieved"


# --- required per month and Original plan ---


def test_required_per_month_spreads_what_is_left_over_the_months_from_today():
    # 14 Oct to 31 Dec 2026 is Oct, Nov, Dec = 3 months; 1200 - 300 left.
    figures = describe(goal(target=1200.0), saved=300.0, today=date(2026, 10, 14))

    assert figures.months_left == 3
    assert figures.remaining == 900.0
    assert figures.required_per_month == pytest.approx(300.0)


def test_an_upcoming_goal_counts_months_from_today_not_from_its_start():
    figures = describe(goal(target=1200.0, start=date(2026, 11, 1)), saved=0.0, today=date(2026, 10, 14))

    assert figures.months_left == 3
    assert figures.required_per_month == pytest.approx(400.0)


def test_required_per_month_is_absent_once_achieved():
    figures = describe(goal(target=1000.0), saved=1000.0, today=date(2026, 6, 15))

    assert figures.required_per_month is None


def test_required_per_month_is_absent_once_the_end_date_has_passed():
    figures = describe(goal(), saved=100.0, today=date(2027, 1, 1))

    assert figures.months_left == 0
    assert figures.required_per_month is None


def test_original_plan_spreads_the_target_over_start_to_end_months():
    # Jan to Dec 2026 is 12 inclusive months.
    figures = describe(goal(target=1200.0), saved=0.0, today=date(2026, 6, 15))

    assert figures.original_plan_per_month == pytest.approx(100.0)


def test_original_plan_for_a_window_inside_one_month_is_the_whole_target():
    figures = describe(
        goal(target=300.0, start=date(2026, 10, 1), end=date(2026, 10, 20)), saved=0.0, today=date(2026, 10, 5)
    )

    assert figures.original_plan_per_month == pytest.approx(300.0)


# --- pace and On track / Behind ---


def test_pace_is_an_even_spread_of_the_target_by_days():
    # 2026-01-01 to 2026-12-31 is 364 days; 2026-07-02 is day 182 = half.
    figures = describe(goal(target=1000.0), saved=0.0, today=date(2026, 7, 2))

    assert figures.pace_fraction == pytest.approx(0.5)
    assert figures.pace_amount == pytest.approx(500.0)


def test_pace_sits_at_zero_until_the_start_date():
    figures = describe(goal(start=date(2026, 7, 1)), saved=0.0, today=date(2026, 6, 15))

    assert figures.pace_fraction == 0.0
    assert figures.pace_amount == 0.0


def test_pace_sits_at_the_target_from_the_end_date():
    figures = describe(goal(target=1000.0), saved=0.0, today=date(2027, 3, 1))

    assert figures.pace_fraction == 1.0
    assert figures.pace_amount == 1000.0


def test_on_track_when_saved_meets_pace():
    figures = describe(goal(target=1000.0), saved=500.0, today=date(2026, 7, 2))

    assert figures.on_track is True
    assert figures.flag == "On track"


def test_behind_when_saved_is_under_pace():
    figures = describe(goal(target=1000.0), saved=400.0, today=date(2026, 7, 2))

    assert figures.on_track is False
    assert figures.flag == "Behind"


def test_a_half_cent_shortfall_still_counts_as_on_track():
    figures = describe(goal(target=1000.0), saved=499.996, today=date(2026, 7, 2))

    assert figures.on_track is True


def test_a_goal_that_has_not_started_is_on_track_with_nothing_saved():
    figures = describe(goal(start=date(2026, 7, 1)), saved=0.0, today=date(2026, 6, 15))

    assert figures.on_track is True


def test_a_zero_length_window_is_treated_as_one_day():
    one_day = goal(target=100.0, start=date(2026, 6, 1), end=date(2026, 6, 1))

    on_the_day = describe(one_day, saved=0.0, today=date(2026, 6, 1))
    after = describe(one_day, saved=0.0, today=date(2026, 6, 2))

    assert on_the_day.pace_fraction == 0.0
    assert on_the_day.status == "Active"
    assert after.pace_fraction == 1.0
    assert after.status == "Ended"


# --- progress ---


def test_fraction_is_capped_at_one_but_over_reports_the_overshoot():
    figures = describe(goal(target=1000.0), saved=1250.0, today=date(2026, 6, 15))

    assert figures.fraction == 1.0
    assert figures.over == 250.0
    assert figures.remaining == 0.0


def test_fraction_is_saved_over_target():
    figures = describe(goal(target=1000.0), saved=250.0, today=date(2026, 6, 15))

    assert figures.fraction == pytest.approx(0.25)
    assert figures.saved == 250.0
