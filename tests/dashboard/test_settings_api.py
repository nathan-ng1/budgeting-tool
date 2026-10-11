"""The Settings tab's localisation settings endpoint (spec #172, Issue #173).

Exercised over real HTTP against a real LocalStore, so a test failing here
means the Dashboard's Settings tab would fail the same way.
"""

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from database.store import connect

DEFAULTS = {"currency": "AUD", "financial_year_start_month": 7, "date_order": "day-first"}


@pytest.fixture
def running_server(serve, store):
    return store, serve(store)


def call(server, method: str, path: str, payload: dict | None = None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"http://127.0.0.1:{server.server_port}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body else {},
    )
    with urlopen(request) as response:
        raw = response.read()
        return response.status, (json.loads(raw) if raw else None)


def test_a_fresh_database_reads_the_australian_defaults(running_server):
    _store, server = running_server

    status, body = call(server, "GET", "/api/settings")

    assert status == 200
    assert body == DEFAULTS


def test_a_saved_currency_reads_back_and_leaves_the_other_settings_alone(running_server):
    _store, server = running_server

    status, saved = call(server, "PUT", "/api/settings", {"currency": "EUR"})
    _status, body = call(server, "GET", "/api/settings")

    assert status == 200
    assert saved == {**DEFAULTS, "currency": "EUR"}
    assert body == {**DEFAULTS, "currency": "EUR"}


def test_all_three_settings_can_be_saved_and_read_back(running_server):
    _store, server = running_server

    call(
        server,
        "PUT",
        "/api/settings",
        {"currency": "JPY", "financial_year_start_month": 4, "date_order": "month-first"},
    )

    _status, body = call(server, "GET", "/api/settings")
    assert body == {"currency": "JPY", "financial_year_start_month": 4, "date_order": "month-first"}


def test_a_saved_setting_survives_a_server_restart(serve, tmp_path):
    database = tmp_path / "budget.db"
    call(serve(connect(database)), "PUT", "/api/settings", {"currency": "GBP"})

    _status, body = call(serve(connect(database)), "GET", "/api/settings")

    assert body["currency"] == "GBP"


@pytest.mark.parametrize(
    "payload, mentions",
    [
        ({"currency": "XYZ"}, "XYZ"),
        ({"currency": 5}, "currency"),
        ({"financial_year_start_month": 0}, "financial_year_start_month"),
        ({"financial_year_start_month": 13}, "financial_year_start_month"),
        ({"financial_year_start_month": "July"}, "financial_year_start_month"),
        ({"date_order": "year-first"}, "year-first"),
        ({"date_order": "Day-First"}, "Day-First"),
        ({"date_order": ""}, "date_order"),
        ({"date_order": None}, "date_order"),
        ({"date_order": 5}, "date_order"),
        ({"date_order": ["day-first"]}, "date_order"),
        ({"surprise": 1}, "surprise"),
    ],
)
def test_an_invalid_value_is_rejected_with_a_clear_error_and_nothing_is_saved(running_server, payload, mentions):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "PUT", "/api/settings", {"currency": "GBP", **payload})

    assert exc_info.value.code == 400
    assert mentions in json.loads(exc_info.value.read())["error"]
    _status, body = call(server, "GET", "/api/settings")
    assert body == DEFAULTS
