import csv
from pathlib import Path

import pytest

from sanitising.sanitise import sanitise

FIXTURES = Path(__file__).parent / "fixtures"


def _read_rows(fixture_name: str) -> list[list[str]]:
    with open(FIXTURES / fixture_name, newline="") as f:
        return list(csv.reader(f))


def test_anz_sanitise_is_a_passthrough():
    raw_rows = _read_rows("anz_sample.csv")

    sanitised_rows = sanitise(raw_rows, "ANZ")

    assert sanitised_rows == raw_rows


def test_unknown_issuer_raises():
    raw_rows = _read_rows("anz_sample.csv")

    with pytest.raises(ValueError):
        sanitise(raw_rows, "UNKNOWN_BANK")
