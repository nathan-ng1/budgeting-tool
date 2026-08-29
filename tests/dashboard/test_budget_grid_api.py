"""The Budget tab's Full year read-only grid endpoint (Issue #64).

Exercised over real HTTP against a real LocalStore, so a test failing here
means the Dashboard's Budget tab's Full year pill would fail the same way.
"""

import json
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pytest


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


def _row(rows, category):
    return next(row for row in rows if row["category"] == category)


def test_a_fresh_financial_year_returns_every_category_grouped_by_type_all_unset(running_server):
    _store, server = running_server

    status, body = call(server, "GET", "/api/budget-grid?year=2026")

    assert status == 200
    assert list(body.keys()) == ["Income", "Expense", "Debt"]
    assert _row(body["Income"], "Salary")["amounts"] == [None] * 12
    assert _row(body["Expense"], "Groceries")["amounts"] == [None] * 12
    assert _row(body["Debt"], "Mortgage Repayment")["amounts"] == [None] * 12
    # Savings has no Category Budget to show (CONTEXT.md).
    assert "Savings" not in body


def test_a_category_budget_saved_via_the_month_editor_appears_in_its_july_to_june_slot(running_server):
    _store, server = running_server

    call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=8", {"amount": 650.0})

    _status, body = call(server, "GET", "/api/budget-grid?year=2026")
    amounts = _row(body["Expense"], "Groceries")["amounts"]

    assert amounts[1] == 650.0  # August is index 1 (July is index 0)
    assert amounts[:1] == [None]
    assert amounts[2:] == [None] * 10


def test_a_category_budget_outside_the_financial_year_does_not_appear(running_server):
    _store, server = running_server

    # June 2026 belongs to the Financial Year starting 2025, not 2026.
    call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=6", {"amount": 999.0})

    _status, body = call(server, "GET", "/api/budget-grid?year=2026")

    assert _row(body["Expense"], "Groceries")["amounts"] == [None] * 12


def test_a_category_with_special_characters_round_trips_through_the_url(running_server):
    _store, server = running_server
    category = "Dining & Takeaway"

    call(server, "PUT", f"/api/budget-editor/{quote(category)}?year=2026&month=7", {"amount": 300.0})

    _status, body = call(server, "GET", "/api/budget-grid?year=2026")
    assert _row(body["Expense"], category)["amounts"][0] == 300.0


def test_the_grid_read_requires_year(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "GET", "/api/budget-grid")

    assert exc_info.value.code == 400


def test_period_calendar_orders_the_grid_january_to_december(running_server):
    _store, server = running_server

    call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=3", {"amount": 400.0})

    _status, body = call(server, "GET", "/api/budget-grid?year=2026&period=calendar")
    amounts = _row(body["Expense"], "Groceries")["amounts"]

    assert amounts[2] == 400.0  # March is index 2 in Jan-Dec order
    assert amounts[:2] == [None, None]
    assert amounts[3:] == [None] * 9


def test_period_omitted_defaults_to_financial_year_ordering(running_server):
    _store, server = running_server

    call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=8", {"amount": 650.0})

    _status, body = call(server, "GET", "/api/budget-grid?year=2026")
    amounts = _row(body["Expense"], "Groceries")["amounts"]

    assert amounts[1] == 650.0  # August is index 1 in Jul-Jun order


def test_the_grid_read_rejects_an_invalid_period(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "GET", "/api/budget-grid?year=2026&period=nonsense")

    assert exc_info.value.code == 400
