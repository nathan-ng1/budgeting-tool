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


def test_beem_sanitise_drops_header_row(monkeypatch):
    monkeypatch.setenv("BEEM_USERNAME", "nathan_ng")
    raw_rows = _read_rows("beem_sample.csv")

    sanitised_rows = sanitise(raw_rows, "Beem")

    assert raw_rows[0] not in sanitised_rows


def test_beem_sanitise_drops_non_payment_rows(monkeypatch):
    monkeypatch.setenv("BEEM_USERNAME", "nathan_ng")
    raw_rows = _read_rows("beem_sample.csv")

    sanitised_rows = sanitise(raw_rows, "Beem")

    assert len(sanitised_rows) == 2
    assert "balance top-up" not in [row[2] for row in sanitised_rows]


def test_beem_sanitise_derives_negative_amount_when_user_is_payer(monkeypatch):
    monkeypatch.setenv("BEEM_USERNAME", "nathan_ng")
    raw_rows = _read_rows("beem_sample.csv")

    sanitised_rows = sanitise(raw_rows, "Beem")

    assert ["30/07/2026", "-15.5", "mahjong + coke"] in sanitised_rows


def test_beem_sanitise_derives_positive_amount_when_user_is_recipient(monkeypatch):
    monkeypatch.setenv("BEEM_USERNAME", "nathan_ng")
    raw_rows = _read_rows("beem_sample.csv")

    sanitised_rows = sanitise(raw_rows, "Beem")

    assert ["28/07/2026", "42.0", "trip repayment"] in sanitised_rows


def test_beem_sanitise_output_rows_have_no_username_or_reference_columns(monkeypatch):
    monkeypatch.setenv("BEEM_USERNAME", "nathan_ng")
    raw_rows = _read_rows("beem_sample.csv")

    sanitised_rows = sanitise(raw_rows, "Beem")

    assert all(len(row) == 3 for row in sanitised_rows)
    flattened = [value for row in sanitised_rows for value in row]
    assert "nathan_ng" not in flattened
    assert "jane_doe" not in flattened
    assert "john_smith" not in flattened
    assert "REF001" not in flattened
    assert "REF002" not in flattened
