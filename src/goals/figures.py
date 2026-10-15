"""Everything the Goals tab shows about a Goal that isn't stored (Goals spec
section 7): Status, pace, On track / Behind, months remaining, required per
month and the Original plan.

Pure calendar and money maths over one `today`, so the tab and the Overview
tile can never disagree. The frontend only formats these.
"""

import calendar
from dataclasses import dataclass
from datetime import date

from goals.goal import Goal

STATUS_ACTIVE = "Active"

# A half-cent: how far under the even pace a Goal may sit and still be On track.
PACE_TOLERANCE = 0.005


@dataclass(frozen=True)
class GoalFigures:
    saved: float
    remaining: float
    over: float
    fraction: float
    status: str
    flag: str
    pace_fraction: float
    pace_amount: float
    on_track: bool
    months_left: int
    required_per_month: float | None
    original_plan_per_month: float


def _shift_months_clamped(start: date, months: int) -> date:
    """`start` shifted by whole calendar months, its day clamped to the target
    month's length (31 Jan + 1 month = 28 Feb)."""
    year, month_index = divmod(start.year * 12 + start.month - 1 + months, 12)
    return date(year, month_index + 1, min(start.day, calendar.monthrange(year, month_index + 1)[1]))


def goal_months(start: date, end: date) -> int:
    """Calendar months from `start` to `end`, counting each month from its
    anniversary of `start` and rounding a partial month up, never below one
    (20 Oct to 20 Dec is 2, 20 Oct to 21 Dec is 3, 20 Oct to 5 Nov is 1)."""
    whole = (end.year - start.year) * 12 + end.month - start.month
    if _shift_months_clamped(start, whole) > end:
        whole -= 1
    anniversary = _shift_months_clamped(start, whole)
    if anniversary < end:
        whole += 1
    return max(1, whole)


def describe(goal: Goal, saved: float, today: date) -> GoalFigures:
    target = goal.target_amount
    achieved = saved >= target

    # Precedence: Achieved, then Ended, then Upcoming, else Active.
    if achieved:
        status = "Achieved"
    elif today > goal.end_date:
        status = "Ended"
    elif today < goal.start_date:
        status = "Upcoming"
    else:
        status = STATUS_ACTIVE

    # The even pace runs by days from start to end; a zero-length window counts
    # as one day, and the marker is clamped to 0 before the start and to the
    # target from the end.
    window_days = max(1, (goal.end_date - goal.start_date).days)
    elapsed_days = min(max((today - goal.start_date).days, 0), window_days)
    pace_fraction = elapsed_days / window_days
    pace_amount = target * pace_fraction
    on_track = saved >= pace_amount - PACE_TOLERANCE

    months_left = 0 if today > goal.end_date else goal_months(today, goal.end_date)
    remaining = max(target - saved, 0.0)

    return GoalFigures(
        saved=saved,
        remaining=remaining,
        over=max(saved - target, 0.0),
        fraction=min(saved / target, 1.0),
        status=status,
        # On track / Behind only means something while the Goal is live.
        flag=("On track" if on_track else "Behind") if status == STATUS_ACTIVE else status,
        pace_fraction=pace_fraction,
        pace_amount=pace_amount,
        on_track=on_track,
        months_left=months_left,
        required_per_month=remaining / months_left if months_left > 0 and not achieved else None,
        original_plan_per_month=target / goal_months(goal.start_date, goal.end_date),
    )
