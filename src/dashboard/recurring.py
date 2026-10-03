"""Translation between the Recurring Transactions Config's JSON shape and
RecurringRule - see Issue #29.

Kept out of dashboard.server so the HTTP layer stays a router: what a rule
looks like on the wire is a question about the domain, not about HTTP.
"""

import math
from dataclasses import replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from recurring.rules import RecurringRule, StoredRecurringRule
from recurring.schedule import expand

FIELDS = (
    "amount",
    "type",
    "category",
    "notes",
    "frequency",
    "interval",
    "day",
    "start_date",
    "end_date",
)


def as_payload(stored: StoredRecurringRule) -> dict:
    rule = stored.rule
    return {
        "id": stored.id,
        "amount": rule.amount,
        "type": rule.type,
        "category": rule.category,
        "notes": rule.notes,
        "frequency": rule.frequency,
        "interval": rule.interval,
        # Day stays whatever kind the Frequency implies: a weekday name for
        # Weekly rules, a day-of-month number for Monthly ones.
        "day": rule.day,
        "start_date": rule.start_date.isoformat(),
        "end_date": rule.end_date.isoformat() if rule.end_date is not None else None,
    }


def from_payload(payload) -> RecurringRule:
    """The RecurringRule a request body describes.

    The body carries either a per-occurrence `amount` or a `total_amount` to
    split evenly across the schedule (Issue #148) - see split_from_payload.
    Either way the result is an ordinary rule; nothing about a split is kept.

    Raises ValueError - with a message naming what's wrong - for anything the
    caller could fix by sending a different body. RecurringRule's own
    __post_init__ raises the same way for a schedule that contradicts itself,
    so the caller has one kind of error to handle.
    """
    if isinstance(payload, dict) and "total_amount" in payload:
        rule, _occurrences = split_from_payload(payload)
        return rule
    return _rule(payload, amount_field="amount")


def split_from_payload(payload) -> tuple[RecurringRule, int]:
    """The RecurringRule a body with a `total_amount` describes, plus how many
    occurrences that Total was split across.

    The per-occurrence Amount is the Total divided by the occurrence count
    `recurring.schedule.expand` gives for the rule's own schedule, rounded to
    the nearest cent - any drift between the rounded occurrences and the
    Total is accepted rather than corrected. An End Date is required, since a
    rule that recurs indefinitely has no count to divide by.
    """
    if isinstance(payload, dict) and "amount" in payload:
        raise ValueError("Send either 'amount' or 'total_amount', not both")

    rule = _rule(payload, amount_field="total_amount")
    if not math.isfinite(rule.amount):
        raise ValueError(f"Field 'total_amount' must be a finite number, got {payload['total_amount']!r}")
    if rule.end_date is None:
        raise ValueError("Field 'end_date' is required when splitting a 'total_amount' across the schedule")

    occurrences = len(expand(rule, through=rule.end_date))
    per_occurrence = (Decimal(str(rule.amount)) / occurrences).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return replace(rule, amount=float(per_occurrence)), occurrences


def _rule(payload, amount_field: str) -> RecurringRule:
    # `amount_field` names whichever field the Amount comes from - for a split
    # that's the Total, which split_from_payload then divides.
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object describing one rule")

    required = [amount_field if field == "amount" else field for field in FIELDS]
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")

    return RecurringRule(
        amount=_number(payload[amount_field], amount_field),
        type=payload["type"],
        category=payload["category"],
        notes=payload["notes"],
        frequency=payload["frequency"],
        interval=_whole_number(payload["interval"], "interval"),
        day=_day(payload["day"], payload["frequency"]),
        start_date=_date(payload["start_date"], "start_date"),
        end_date=_date(payload["end_date"], "end_date") if payload["end_date"] else None,
    )


def _day(value, frequency):
    # A Monthly Day arrives as a number, but a <select> may well send "15";
    # accept either rather than making the frontend's input type load-bearing.
    if frequency == "Monthly":
        return _whole_number(value, "day")
    return value


def _number(value, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Field {field!r} must be a number, got {value!r}") from None


def _whole_number(value, field: str) -> int:
    # int() would truncate a fractional JSON number rather than refuse it, so
    # an Interval of 2.9 would silently become 2.
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"Field {field!r} must be a whole number, got {value!r}") from None

    if not number.is_integer():
        raise ValueError(f"Field {field!r} must be a whole number, got {value!r}")
    return int(number)


def _date(value, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"Field {field!r} must be a date as YYYY-MM-DD, got {value!r}") from None
