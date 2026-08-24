"""The Budget tab's standing Budget Suggestion read endpoint (Issue #66).

Exercised over real HTTP against a real LocalStore, so a test failing here
means the Dashboard's Budget tab's write-up would fail the same way.
"""

import json
from datetime import datetime
from urllib.request import Request, urlopen

import pytest


@pytest.fixture
def running_server(serve, store):
    return store, serve(store)


def call(server, method: str, path: str):
    request = Request(f"http://127.0.0.1:{server.server_port}{path}", method=method)
    with urlopen(request) as response:
        raw = response.read()
        return response.status, (json.loads(raw) if raw else None)


def test_a_store_with_no_write_up_yet_returns_nulls_not_an_error(running_server):
    _store, server = running_server

    status, body = call(server, "GET", "/api/budget-suggestion")

    assert status == 200
    assert body == {"write_up": None, "generated_at": None}


def test_a_stored_write_up_is_returned_as_is(running_server):
    store, server = running_server
    store.write_budget_suggestion("Groceries has run over budget three months running.", datetime(2026, 8, 20, 14, 32))

    status, body = call(server, "GET", "/api/budget-suggestion")

    assert status == 200
    assert body == {
        "write_up": "Groceries has run over budget three months running.",
        "generated_at": "2026-08-20T14:32:00",
    }


def test_the_write_up_is_the_same_regardless_of_any_month_query_param(running_server):
    """The endpoint takes no (year, month) at all - it is one standing
    write-up, not scoped to a month (CONTEXT.md's Budget Suggestion entry)."""
    store, server = running_server
    store.write_budget_suggestion("Standing advice.", datetime(2026, 8, 20, 14, 32))

    _status, plain = call(server, "GET", "/api/budget-suggestion")
    _status, with_query = call(server, "GET", "/api/budget-suggestion?year=2026&month=9")

    assert plain == with_query
