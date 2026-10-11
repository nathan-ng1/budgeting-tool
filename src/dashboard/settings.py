"""The localisation settings (ADR-0027): what they may hold, their defaults,
and their JSON shape - kept out of dashboard.server so the HTTP layer stays a
router.

Only the *identifiers* of the Display Currency entries live here, to validate
a save. Each entry's symbol, separators and sample belong to the frontend's
curated list (frontend/src/lib/currencies.js); the two lists must name the
same entries (tests/dashboard/test_currency_parity.py fails when they drift).
"""

DEFAULTS = {
    "currency": "AUD",
    "financial_year_start_month": 7,
    "date_order": "day-first",
}

DATE_ORDERS = ("day-first", "month-first")

CURRENCY_IDS = frozenset(
    {
        "AUD", "NZD", "USD", "CAD", "GBP", "JPY", "CNY", "KRW", "INR", "SGD", "HKD", "ZAR", "AED",
        "CHF", "SEK", "NOK", "DKK", "PLN", "CZK", "BRL", "MXN", "EUR",
    }
)  # fmt: skip


def as_payload(saved: dict[str, str]) -> dict:
    """Every setting, with the default filled in for any never saved."""
    merged = {**DEFAULTS, **saved}
    merged["financial_year_start_month"] = int(merged["financial_year_start_month"])
    return merged


def financial_year_start_month(saved: dict[str, str]) -> int:
    """The Financial Year start month (1-12), the default if never saved."""
    return as_payload(saved)["financial_year_start_month"]


def updates_from_payload(payload) -> dict:
    """The validated settings a save request body describes - any subset of
    the three. Raises ValueError, naming the offending field, on anything else.
    """
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object of settings")

    unknown = [key for key in payload if key not in DEFAULTS]
    if unknown:
        raise ValueError(f"Unknown setting(s): {', '.join(unknown)}")

    validators = {
        "currency": _currency,
        "financial_year_start_month": _start_month,
        "date_order": _date_order,
    }
    return {key: validators[key](value) for key, value in payload.items()}


def _currency(value) -> str:
    if not isinstance(value, str) or value not in CURRENCY_IDS:
        raise ValueError(f"currency {value!r} is not an available Display Currency")
    return value


def _start_month(value) -> int:
    # bool is an int subclass; True is not a month.
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 12:
        raise ValueError(f"financial_year_start_month must be a month number from 1 to 12, got {value!r}")
    return value


def _date_order(value) -> str:
    if value not in DATE_ORDERS:
        raise ValueError(f"date_order must be one of {', '.join(DATE_ORDERS)}, got {value!r}")
    return value
