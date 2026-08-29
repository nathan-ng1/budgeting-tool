"""The Category Management CRUD endpoint (Issue #91).

Exercised over real HTTP against a real LocalStore, so a test failing here
means the Settings screen's Category Management card would fail the same way.
Mirrors tests/dashboard/test_recurring_api.py's call()/running_server pattern.
"""

import json
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


def by_name(body, name):
    return next(category for category in body if category["name"] == name)


def test_listing_categories_offers_id_type_name_emoji_and_locked(running_server):
    _store, server = running_server

    status, body = call(server, "GET", "/api/categories")

    assert status == 200
    groceries = by_name(body, "Groceries")
    assert groceries["type"] == "Expense"
    assert groceries["emoji"] is None
    assert groceries["locked"] is False
    assert isinstance(groceries["id"], int)


def test_beem_adjustment_is_listed_as_locked(running_server):
    _store, server = running_server

    _status, body = call(server, "GET", "/api/categories")

    assert by_name(body, "Beem Adjustment")["locked"] is True


def test_creating_a_category_without_an_emoji_returns_it_with_the_id_the_store_gave_it(running_server):
    _store, server = running_server

    status, created = call(server, "POST", "/api/categories", {"type": "Expense", "name": "Pets"})

    assert status == 201
    assert created["id"] is not None
    assert created == {"id": created["id"], "type": "Expense", "name": "Pets", "emoji": None, "locked": False}


def test_creating_a_category_with_an_emoji_round_trips_it(running_server):
    _store, server = running_server

    _status, created = call(server, "POST", "/api/categories", {"type": "Expense", "name": "Pets", "emoji": "🐾"})

    assert created["emoji"] == "🐾"


def test_a_created_category_then_appears_in_the_listing(running_server):
    _store, server = running_server
    _status, created = call(server, "POST", "/api/categories", {"type": "Expense", "name": "Pets", "emoji": "🐾"})

    _status, listed = call(server, "GET", "/api/categories")

    assert created in listed


def test_creating_a_category_rejects_a_name_that_collides_across_types(running_server):
    _store, server = running_server
    call(server, "POST", "/api/categories", {"type": "Expense", "name": "Pets"})

    with pytest.raises(HTTPError) as exc_info:
        call(server, "POST", "/api/categories", {"type": "Income", "name": "Pets"})

    assert exc_info.value.code == 400
    assert "Pets" in json.loads(exc_info.value.read())["error"]


def test_creating_a_category_rejects_a_type_outside_the_four_fixed_ones(running_server):
    _store, server = running_server

    # Transfer is ADR-0022's retired name for this Type - no longer valid.
    with pytest.raises(HTTPError) as exc_info:
        call(server, "POST", "/api/categories", {"type": "Transfer", "name": "Piggy Bank"})

    assert exc_info.value.code == 400
    assert "Transfer" in json.loads(exc_info.value.read())["error"]


def test_a_payload_missing_a_name_is_rejected_with_a_clear_error(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "POST", "/api/categories", {"type": "Expense"})

    assert exc_info.value.code == 400
    assert "name" in json.loads(exc_info.value.read())["error"]


def test_renaming_a_category_works_in_place(running_server):
    _store, server = running_server
    _status, created = call(server, "POST", "/api/categories", {"type": "Expense", "name": "Pets", "emoji": "🐾"})

    status, updated = call(server, "PUT", f"/api/categories/{created['id']}", {"name": "Pet Care", "emoji": "🐾"})

    assert status == 200
    assert updated["id"] == created["id"]
    assert updated["name"] == "Pet Care"
    assert updated["type"] == "Expense"


def test_changing_only_the_emoji_leaves_the_name_alone(running_server):
    _store, server = running_server
    _status, created = call(server, "POST", "/api/categories", {"type": "Expense", "name": "Pets"})

    _status, updated = call(server, "PUT", f"/api/categories/{created['id']}", {"name": "Pets", "emoji": "🐶"})

    assert updated["name"] == "Pets"
    assert updated["emoji"] == "🐶"


def test_renaming_a_category_into_a_name_that_collides_is_rejected(running_server):
    _store, server = running_server
    call(server, "POST", "/api/categories", {"type": "Expense", "name": "Pets"})
    _status, other = call(server, "POST", "/api/categories", {"type": "Expense", "name": "Hobbies"})

    with pytest.raises(HTTPError) as exc_info:
        call(server, "PUT", f"/api/categories/{other['id']}", {"name": "Pets"})

    assert exc_info.value.code == 400


def test_renaming_a_category_that_does_not_exist_returns_404(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "PUT", "/api/categories/404", {"name": "Pets"})

    assert exc_info.value.code == 404


def test_deleting_an_unused_category_removes_it_from_the_listing(running_server):
    _store, server = running_server
    _status, created = call(server, "POST", "/api/categories", {"type": "Expense", "name": "Pets"})

    status, _body = call(server, "DELETE", f"/api/categories/{created['id']}")

    assert status == 204
    _status, listed = call(server, "GET", "/api/categories")
    assert all(category["id"] != created["id"] for category in listed)


def test_deleting_a_category_that_does_not_exist_returns_404(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "DELETE", "/api/categories/404")

    assert exc_info.value.code == 404


def test_deleting_a_category_referenced_by_a_transaction_is_rejected(running_server):
    store, server = running_server
    _status, created = call(server, "POST", "/api/categories", {"type": "Expense", "name": "Pets"})
    call(
        server,
        "POST",
        "/api/transactions",
        {"date": "2026-08-05", "amount": 42.5, "type": "Expense", "category": "Pets", "notes": "Vet"},
    )

    with pytest.raises(HTTPError) as exc_info:
        call(server, "DELETE", f"/api/categories/{created['id']}")

    assert exc_info.value.code == 400
    assert "Pets" in json.loads(exc_info.value.read())["error"]
    assert any(category.name == "Pets" for category in store.read_categories())


def test_deleting_a_category_referenced_by_a_recurring_rule_is_rejected(running_server):
    _store, server = running_server
    _status, created = call(server, "POST", "/api/categories", {"type": "Expense", "name": "Pets"})
    call(
        server,
        "POST",
        "/api/recurring-rules",
        {
            "amount": 50.0,
            "type": "Expense",
            "category": "Pets",
            "notes": "Vet insurance",
            "frequency": "Monthly",
            "interval": 1,
            "day": 5,
            "start_date": "2026-08-05",
            "end_date": None,
        },
    )

    with pytest.raises(HTTPError) as exc_info:
        call(server, "DELETE", f"/api/categories/{created['id']}")

    assert exc_info.value.code == 400
    assert "Pets" in json.loads(exc_info.value.read())["error"]


def test_deleting_a_category_referenced_by_a_category_budget_is_rejected(running_server):
    store, server = running_server
    _status, created = call(server, "POST", "/api/categories", {"type": "Expense", "name": "Pets"})
    store.upsert_category_budget("Expense", "Pets", 2026, 8, 100.0)

    with pytest.raises(HTTPError) as exc_info:
        call(server, "DELETE", f"/api/categories/{created['id']}")

    assert exc_info.value.code == 400
    assert "Pets" in json.loads(exc_info.value.read())["error"]


def test_renaming_a_locked_category_is_rejected(running_server):
    _store, server = running_server
    _status, body = call(server, "GET", "/api/categories")
    beem = by_name(body, "Beem Adjustment")

    with pytest.raises(HTTPError) as exc_info:
        call(server, "PUT", f"/api/categories/{beem['id']}", {"name": "Not Beem Adjustment"})

    assert exc_info.value.code == 400
    assert "locked" in json.loads(exc_info.value.read())["error"].lower()


def test_deleting_a_locked_category_is_rejected(running_server):
    _store, server = running_server
    _status, body = call(server, "GET", "/api/categories")
    beem = by_name(body, "Beem Adjustment")

    with pytest.raises(HTTPError) as exc_info:
        call(server, "DELETE", f"/api/categories/{beem['id']}")

    assert exc_info.value.code == 400
    assert "locked" in json.loads(exc_info.value.read())["error"].lower()


def test_a_body_that_is_not_json_is_rejected(running_server):
    _store, server = running_server
    request = Request(
        f"http://127.0.0.1:{server.server_port}/api/categories",
        data=b"not json at all",
        method="POST",
    )

    with pytest.raises(HTTPError) as exc_info:
        urlopen(request)

    assert exc_info.value.code == 400


def test_a_category_created_through_the_endpoint_is_immediately_usable_by_a_transaction(running_server):
    _store, server = running_server
    call(server, "POST", "/api/categories", {"type": "Expense", "name": "Pets", "emoji": "🐾"})

    status, created = call(
        server,
        "POST",
        "/api/transactions",
        {"date": "2026-08-05", "amount": 42.5, "type": "Expense", "category": "Pets", "notes": "Vet"},
    )

    assert status == 201
    assert created["category"] == "Pets"
