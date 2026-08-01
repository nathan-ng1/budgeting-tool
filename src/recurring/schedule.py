from calendar import monthrange
from datetime import date, timedelta

from recurring.rules import Occurrence, RecurringRule


def expand(rule: RecurringRule, through: date) -> list[Occurrence]:
    if rule.frequency == "Weekly":
        dates = _expand_weekly(rule, through)
    else:
        dates = _expand_monthly(rule, through)

    return [
        Occurrence(
            date=d,
            amount=rule.amount,
            category=rule.category,
            sub_category=rule.sub_category,
            notes=rule.notes,
        )
        for d in dates
    ]


def _within_range(occurrence: date, rule: RecurringRule, through: date) -> bool:
    if occurrence > through:
        return False
    if rule.end_date is not None and occurrence > rule.end_date:
        return False
    return True


def _expand_weekly(rule: RecurringRule, through: date) -> list[date]:
    dates = []
    current = rule.start_date
    step = timedelta(weeks=rule.interval)
    while _within_range(current, rule, through):
        dates.append(current)
        current += step
    return dates


def _expand_monthly(rule: RecurringRule, through: date) -> list[date]:
    dates = []
    k = 0
    while True:
        occurrence = rule.start_date if k == 0 else _monthly_occurrence(rule, k)
        if not _within_range(occurrence, rule, through):
            break
        dates.append(occurrence)
        k += 1
    return dates


def _monthly_occurrence(rule: RecurringRule, k: int) -> date:
    month_index = (rule.start_date.month - 1) + k * rule.interval
    year = rule.start_date.year + month_index // 12
    month = month_index % 12 + 1
    last_day_of_month = monthrange(year, month)[1]
    day = min(rule.day, last_day_of_month)
    return date(year, month, day)
