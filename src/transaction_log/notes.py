"""Notes normalisation, shared by History Matches (ADR-0026) and the Dashboard's
recurring-charges view."""

import re

_DIGITS = re.compile(r"\d")
_WHITESPACE = re.compile(r"\s+")


def normalise_notes(notes: str) -> str:
    """Lowercase, strip every digit, collapse whitespace, trim - so store
    numbers, terminal IDs, case and spacing don't defeat the lookup."""
    return _WHITESPACE.sub(" ", _DIGITS.sub("", notes.lower())).strip()
