"""The Transactions tab's read endpoint (Issue #33).

Exercised over real HTTP against a real LocalStore, mirroring
tests/dashboard/test_recurring_api.py - a test failing here means the
Dashboard's Transactions tab would fail the same way.
"""

import json
from datetime import date
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest


@pytest.fixture
def running_server(serve, store):
    return store, serve(store)


def get(server, path: str):
    with urlopen(f"http://127.0.0.1:{server.server_port}{path}") as response:
        return response.status, json.loads(response.read())


def test_listing_on_an_empty_financial_year_returns_an_empty_list(running_server):
    _store, server = running_server

    status, body = get(server, "/api/transactions?year=2026&month=7")

    assert status == 200
    assert body == []


def test_listing_returns_the_financial_years_transactions_newest_first_with_ids(
    running_server, make_candidate
):
    store, server = running_server
    store.append_rows(
        [
            make_candidate(date=date(2026, 8, 1), amount=42.5, type="Expense", category="Groceries", notes="Woolworths"),
            make_candidate(date=date(2027, 3, 1), amount=4000.0, type="Income", category="Salary", notes="Employer"),
        ]
    )

    status, body = get(server, "/api/transactions?year=2026&month=7")

    assert status == 200
    assert [row["notes"] for row in body] == ["Employer", "Woolworths"]
    assert all(row["id"] is not None for row in body)
    assert body[0] == {
        "id": body[0]["id"],
        "date": "2027-03-01",
        "amount": 4000.0,
        "type": "Income",
        "category": "Salary",
        "notes": "Employer",
    }


def test_listing_excludes_transactions_outside_the_financial_year(running_server, make_candidate):
    store, server = running_server
    store.append_rows(
        [
            make_candidate(date=date(2026, 6, 30), notes="Last day of the prior Financial Year"),
            make_candidate(date=date(2027, 7, 1), notes="First day of the next Financial Year"),
            make_candidate(date=date(2026, 8, 15), notes="In the Financial Year"),
        ]
    )

    _status, body = get(server, "/api/transactions?year=2026&month=7")

    assert [row["notes"] for row in body] == ["In the Financial Year"]


def test_missing_query_params_returns_400(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        urlopen(f"http://127.0.0.1:{server.server_port}/api/transactions")

    assert exc_info.value.code == 400
