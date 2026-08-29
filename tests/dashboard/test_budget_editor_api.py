"""The Budget tab's per-month editor endpoint (Issue #62).

Exercised over real HTTP against a real LocalStore, so a test failing here
means the Dashboard's Budget screen would fail the same way.
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


def test_a_fresh_month_returns_every_category_grouped_by_type_all_unset(running_server):
    _store, server = running_server

    status, body = call(server, "GET", "/api/budget-editor?year=2026&month=8")

    assert status == 200
    assert list(body.keys()) == ["Income", "Expense", "Debt"]
    assert _row(body["Income"], "Salary")["amount"] is None
    assert _row(body["Expense"], "Groceries")["amount"] is None
    assert _row(body["Debt"], "Mortgage Repayment")["amount"] is None
    # Savings has no Category Budget to set (CONTEXT.md).
    assert "Savings" not in body
    # A fresh store has no Transaction history at all, so the windowed
    # historical columns are unset - not a misleadingly small average.
    salary = _row(body["Income"], "Salary")
    assert salary["last_month_actual"] == 0.0
    assert salary["trailing_average_actual"] is None
    assert salary["average_variance_pct"] is None
    assert salary["month_actual"] == 0.0


def test_saving_a_category_budget_then_appears_in_the_editor_read(running_server):
    _store, server = running_server

    status, saved = call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=8", {"amount": 650.0})

    assert status == 200
    assert saved == {"category": "Groceries", "amount": 650.0}

    _status, body = call(server, "GET", "/api/budget-editor?year=2026&month=8")
    assert _row(body["Expense"], "Groceries")["amount"] == 650.0


def test_month_actual_reflects_the_selected_months_known_transactions(running_server):
    _store, server = running_server
    call(
        server,
        "POST",
        "/api/transactions",
        {
            "date": "2026-08-05",
            "amount": 310.0,
            "type": "Expense",
            "category": "Groceries",
            "notes": "Woolworths",
        },
    )

    _status, body = call(server, "GET", "/api/budget-editor?year=2026&month=8")

    # A separate, necessary seam from the query-layer test: as_editor_payload's
    # field mapping is manual, so a value computed correctly by
    # get_budget_editor could still be silently omitted from the wire
    # contract if the key isn't added there too.
    assert _row(body["Expense"], "Groceries")["month_actual"] == 310.0


def test_last_months_own_category_budget_appears_as_last_month_budgeted(running_server):
    _store, server = running_server

    call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=7", {"amount": 280.0})

    _status, body = call(server, "GET", "/api/budget-editor?year=2026&month=8")
    assert _row(body["Expense"], "Groceries")["last_month_budgeted"] == 280.0
    assert _row(body["Expense"], "Transport")["last_month_budgeted"] is None


def test_saving_a_category_budget_for_one_month_does_not_affect_another(running_server):
    store, server = running_server

    call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=8", {"amount": 650.0})

    _status, september = call(server, "GET", "/api/budget-editor?year=2026&month=9")
    assert _row(september["Expense"], "Groceries")["amount"] is None
    assert store.read_category_budgets(2026, 9) == {}


def test_the_editor_read_accepts_a_trailing_window_query_param(running_server):
    _store, server = running_server

    status, body = call(server, "GET", "/api/budget-editor?year=2026&month=8&window=12")

    assert status == 200
    assert _row(body["Income"], "Salary")["trailing_average_actual"] is None


def test_the_editor_read_rejects_a_trailing_window_outside_3_6_12(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "GET", "/api/budget-editor?year=2026&month=8&window=4")

    assert exc_info.value.code == 400


def test_a_category_with_special_characters_round_trips_through_the_url(running_server):
    _store, server = running_server
    category = "Dining & Takeaway"

    status, saved = call(
        server, "PUT", f"/api/budget-editor/{quote(category)}?year=2026&month=8", {"amount": 300.0}
    )

    assert status == 200
    assert saved == {"category": category, "amount": 300.0}


def test_saving_a_category_budget_twice_updates_it_in_place_not_duplicates(running_server):
    store, server = running_server

    call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=8", {"amount": 650.0})
    call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=8", {"amount": 700.0})

    assert store.read_category_budgets(2026, 8) == {"Groceries": 700.0}


def test_deleting_a_category_budget_removes_it_and_only_it(running_server):
    store, server = running_server
    call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=8", {"amount": 650.0})
    call(server, "PUT", "/api/budget-editor/Transport?year=2026&month=8", {"amount": 120.0})

    status, _body = call(server, "DELETE", "/api/budget-editor/Groceries?year=2026&month=8")

    assert status == 204
    assert store.read_category_budgets(2026, 8) == {"Transport": 120.0}


def test_deleting_a_category_budget_that_was_never_set_is_a_no_op(running_server):
    store, server = running_server

    status, _body = call(server, "DELETE", "/api/budget-editor/Groceries?year=2026&month=8")

    assert status == 204
    assert store.read_category_budgets(2026, 8) == {}


def test_a_category_added_through_category_management_can_have_a_budget_set(running_server):
    # Issue #90 - Type lookup must read the live `categories` table, not the
    # hardcoded CATEGORIES_BY_TYPE dict, or a Category added after startup is
    # wrongly rejected as "not a valid Category".
    store, server = running_server
    store.create_category("Expense", "Pet Care", None)

    status, saved = call(server, "PUT", f"/api/budget-editor/{quote('Pet Care')}?year=2026&month=8", {"amount": 60.0})

    assert status == 200
    assert saved == {"category": "Pet Care", "amount": 60.0}


def test_saving_an_invalid_category_is_rejected(running_server):
    store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "PUT", "/api/budget-editor/NotACategory?year=2026&month=8", {"amount": 100.0})

    assert exc_info.value.code == 400
    assert "NotACategory" in json.loads(exc_info.value.read())["error"]
    assert store.read_category_budgets(2026, 8) == {}


def test_saving_with_a_missing_amount_field_is_rejected(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=8", {})

    assert exc_info.value.code == 400
    assert "amount" in json.loads(exc_info.value.read())["error"]


def test_saving_with_a_non_numeric_amount_is_rejected(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "PUT", "/api/budget-editor/Groceries?year=2026&month=8", {"amount": "not a number"})

    assert exc_info.value.code == 400


def test_the_editor_read_requires_year_and_month(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "GET", "/api/budget-editor?year=2026")

    assert exc_info.value.code == 400


def test_saving_requires_year_and_month(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "PUT", "/api/budget-editor/Groceries?year=2026", {"amount": 100.0})

    assert exc_info.value.code == 400


def test_deleting_requires_year_and_month(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "DELETE", "/api/budget-editor/Groceries?year=2026")

    assert exc_info.value.code == 400
