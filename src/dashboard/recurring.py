"""Translation between the Recurring Transactions Config's JSON shape and
RecurringRule - see Issue #29.

Kept out of dashboard.server so the HTTP layer stays a router: what a rule
looks like on the wire is a question about the domain, not about HTTP.
"""

from datetime import date

from recurring.rules import RecurringRule, StoredRecurringRule

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

    Raises ValueError - with a message naming what's wrong - for anything the
    caller could fix by sending a different body. RecurringRule's own
    __post_init__ raises the same way for a schedule that contradicts itself,
    so the caller has one kind of error to handle.
    """
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object describing one rule")

    missing = [field for field in FIELDS if field not in payload]
    if missing:
        raise ValueError(f"Missing required field(s): {', '.join(missing)}")

    return RecurringRule(
        amount=_number(payload["amount"], "amount"),
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
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Field {field!r} must be a whole number, got {value!r}") from None


def _date(value, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"Field {field!r} must be a date as YYYY-MM-DD, got {value!r}") from None
