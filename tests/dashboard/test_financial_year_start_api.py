"""The Financial Year start month setting reaching the annual overview and the
Budget grid (spec #172, Issue #174).

Exercised over real HTTP against a real LocalStore: when the frontend asks for
the `financial` period, the server resolves it to the saved start month.
"""

import json
from datetime import date
from urllib.error import HTTPError
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


def save_start_month(server, month: int):
    call(server, "PUT", "/api/settings", {"financial_year_start_month": month})


def groceries(grid):
    return next(row for row in grid["Expense"] if row["category"] == "Groceries")["amounts"]


def test_a_saved_april_start_orders_the_financial_grid_april_to_march(running_server):
    _store, server = running_server
    save_start_month(server, 4)
    call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=5", {"amount": 650.0})
    call(server, "PUT", "/api/budget-editor/Groceries?year=2027&month=3", {"amount": 700.0})

    _status, grid = call(server, "GET", "/api/budget-grid?year=2026&period=financial")
    amounts = groceries(grid)

    assert amounts[1] == 650.0  # May is index 1 in Apr-Mar order
    assert amounts[11] == 700.0  # March of the following year is last
    assert amounts[0] is None


def test_an_omitted_period_follows_the_saved_start_month(running_server):
    _store, server = running_server
    save_start_month(server, 4)
    call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=5", {"amount": 650.0})

    _status, grid = call(server, "GET", "/api/budget-grid?year=2026")

    assert groceries(grid)[1] == 650.0


def test_calendar_stays_january_to_december_whatever_the_saved_start_month(running_server):
    _store, server = running_server
    save_start_month(server, 4)
    call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=3", {"amount": 400.0})

    _status, grid = call(server, "GET", "/api/budget-grid?year=2026&period=calendar")

    assert groceries(grid)[2] == 400.0


def test_changing_the_start_month_leaves_every_saved_category_budget_unchanged(running_server):
    _store, server = running_server
    call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=8", {"amount": 650.0})
    _status, before = call(server, "GET", "/api/budget-editor?year=2026&month=8")

    save_start_month(server, 4)
    save_start_month(server, 1)
    _status, after = call(server, "GET", "/api/budget-editor?year=2026&month=8")

    assert after == before
    _status, grid = call(server, "GET", "/api/budget-grid?year=2026")
    assert groceries(grid)[7] == 650.0  # August in Jan-Dec order


def test_the_annual_overview_follows_a_saved_april_start(running_server, make_candidate):
    store, server = running_server
    save_start_month(server, 4)
    store.append_rows(
        [make_candidate(date=date(2024, 4, 10), amount=100.0, type="Income", category="Salary", notes="Employer")]
    )

    _status, body = call(server, "GET", "/api/annual-overview?year=2024&period=financial")

    assert body["elapsed_months"] == 12
    assert body["stat_tiles"]["income"] == 100.0  # April 2024 is inside the 2024 Financial Year
    months = [(row["year"], row["month"]) for row in body["month_by_month"]]
    assert months[0] == (2024, 4)
    assert months[-1] == (2025, 3)


def test_full_year_to_date_counts_elapsed_months_from_the_saved_start_month(running_server):
    _store, server = running_server
    save_start_month(server, 4)
    today = date.today()
    year = today.year if today.month >= 4 else today.year - 1

    _status, body = call(server, "GET", f"/api/annual-overview?year={year}&period=financial")

    # April counts as month 1, so this month is month (today.month - 4 + 1), wrapping the year.
    assert body["elapsed_months"] == (today.month - 4) % 12 + 1


def test_the_annual_overview_calendar_period_stays_january_whatever_the_saved_start_month(running_server):
    _store, server = running_server
    save_start_month(server, 4)

    _status, body = call(server, "GET", "/api/annual-overview?year=2024&period=calendar")

    assert (body["month_by_month"][0]["year"], body["month_by_month"][0]["month"]) == (2024, 1)


def test_the_settings_api_rejects_a_start_month_outside_1_to_12_with_a_clear_400(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "PUT", "/api/settings", {"financial_year_start_month": 13})

    assert exc_info.value.code == 400
    assert "month number from 1 to 12" in json.loads(exc_info.value.read())["error"]
