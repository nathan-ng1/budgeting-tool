"""The Recurring Transactions Config CRUD endpoint (Issue #29).

Exercised over real HTTP against a real LocalStore, so a test failing here
means the Dashboard's Settings screen would fail the same way.
"""

import json
from datetime import date
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from recurring.rules import RecurringRule

WEEKLY_PAYLOAD = {
    "amount": 100.0,
    "type": "Expense",
    "category": "Subscriptions",
    "notes": "Streaming service",
    "frequency": "Weekly",
    "interval": 1,
    "day": "Wednesday",
    "start_date": "2026-08-05",
    "end_date": None,
}

MONTHLY_PAYLOAD = {
    "amount": 4200.0,
    "type": "Income",
    "category": "Salary",
    "notes": "Employer Pty Ltd",
    "frequency": "Monthly",
    "interval": 1,
    "day": 15,
    "start_date": "2026-01-15",
    "end_date": "2026-12-31",
}


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


def test_listing_rules_on_a_fresh_database_returns_an_empty_list(running_server):
    _store, server = running_server

    status, body = call(server, "GET", "/api/recurring-rules")

    assert status == 200
    assert body == []


def test_creating_a_rule_returns_it_with_the_id_the_store_gave_it(running_server):
    _store, server = running_server

    status, created = call(server, "POST", "/api/recurring-rules", WEEKLY_PAYLOAD)

    assert status == 201
    assert created["id"] is not None
    assert {key: created[key] for key in WEEKLY_PAYLOAD} == WEEKLY_PAYLOAD


def test_a_created_rule_then_appears_in_the_listing(running_server):
    _store, server = running_server
    _status, created = call(server, "POST", "/api/recurring-rules", WEEKLY_PAYLOAD)

    _status, listed = call(server, "GET", "/api/recurring-rules")

    assert listed == [created]


def test_a_monthly_rule_keeps_its_day_of_month_as_a_number(running_server):
    _store, server = running_server

    _status, created = call(server, "POST", "/api/recurring-rules", MONTHLY_PAYLOAD)

    assert created["day"] == 15
    assert created["end_date"] == "2026-12-31"


def test_a_rule_created_through_the_endpoint_is_what_the_next_expansion_reads(running_server):
    store, server = running_server

    call(server, "POST", "/api/recurring-rules", WEEKLY_PAYLOAD)

    assert store.read_recurring_rules() == [
        RecurringRule(
            amount=100.0,
            type="Expense",
            category="Subscriptions",
            notes="Streaming service",
            frequency="Weekly",
            interval=1,
            day="Wednesday",
            start_date=date(2026, 8, 5),
            end_date=None,
        )
    ]


def test_editing_a_rule_replaces_it_in_place(running_server):
    store, server = running_server
    _status, created = call(server, "POST", "/api/recurring-rules", WEEKLY_PAYLOAD)

    status, updated = call(
        server, "PUT", f"/api/recurring-rules/{created['id']}", {**WEEKLY_PAYLOAD, "amount": 150.0}
    )

    assert status == 200
    assert updated["id"] == created["id"]
    assert updated["amount"] == 150.0
    assert [rule.amount for rule in store.read_recurring_rules()] == [150.0]


def test_deleting_a_rule_removes_it_from_the_listing_and_from_expansion(running_server):
    store, server = running_server
    _status, created = call(server, "POST", "/api/recurring-rules", WEEKLY_PAYLOAD)

    status, _body = call(server, "DELETE", f"/api/recurring-rules/{created['id']}")

    assert status == 204
    assert call(server, "GET", "/api/recurring-rules")[1] == []
    assert store.read_recurring_rules() == []


def test_creating_a_rule_with_an_invalid_type_category_pair_is_rejected(running_server):
    store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "POST", "/api/recurring-rules", {**WEEKLY_PAYLOAD, "category": "Salary"})

    assert exc_info.value.code == 400
    assert "Salary" in json.loads(exc_info.value.read())["error"]
    assert store.read_recurring_rules() == []


def test_editing_a_rule_into_an_invalid_pair_is_rejected_and_leaves_it_alone(running_server):
    store, server = running_server
    _status, created = call(server, "POST", "/api/recurring-rules", WEEKLY_PAYLOAD)

    with pytest.raises(HTTPError) as exc_info:
        call(server, "PUT", f"/api/recurring-rules/{created['id']}", {**WEEKLY_PAYLOAD, "category": "Salary"})

    assert exc_info.value.code == 400
    assert [rule.category for rule in store.read_recurring_rules()] == ["Subscriptions"]


def test_a_schedule_that_contradicts_itself_is_rejected(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        # 2026-08-05 is a Wednesday, so a rule saying Monday can't start there.
        call(server, "POST", "/api/recurring-rules", {**WEEKLY_PAYLOAD, "day": "Monday"})

    assert exc_info.value.code == 400
    assert "Monday" in json.loads(exc_info.value.read())["error"]


def test_a_payload_missing_a_field_is_rejected_with_a_clear_error(running_server):
    _store, server = running_server
    incomplete = {key: value for key, value in WEEKLY_PAYLOAD.items() if key != "frequency"}

    with pytest.raises(HTTPError) as exc_info:
        call(server, "POST", "/api/recurring-rules", incomplete)

    assert exc_info.value.code == 400
    assert "frequency" in json.loads(exc_info.value.read())["error"]


def test_a_body_that_is_not_json_is_rejected(running_server):
    _store, server = running_server
    request = Request(
        f"http://127.0.0.1:{server.server_port}/api/recurring-rules",
        data=b"not json at all",
        method="POST",
    )

    with pytest.raises(HTTPError) as exc_info:
        urlopen(request)

    assert exc_info.value.code == 400


def test_editing_a_rule_that_does_not_exist_returns_404(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "PUT", "/api/recurring-rules/404", WEEKLY_PAYLOAD)

    assert exc_info.value.code == 404


def test_deleting_a_rule_that_does_not_exist_returns_404(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "DELETE", "/api/recurring-rules/404")

    assert exc_info.value.code == 404


def test_a_non_numeric_rule_id_returns_404(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "DELETE", "/api/recurring-rules/not-a-number")

    assert exc_info.value.code == 404


def test_the_categories_endpoint_offers_the_valid_pairs_the_form_can_choose_from(running_server):
    _store, server = running_server

    status, body = call(server, "GET", "/api/categories")

    assert status == 200
    assert "Salary" in body["Income"]
    assert "Subscriptions" in body["Expense"]
    # Transfer has no Categories yet, so it can't form a valid pair - offering
    # it would let the form build a rule the store then rejects.
    assert "Transfer" not in body


def expanded_notes_and_amounts(store, through: date):
    """What the next Statement Export run would write from the Config alone."""
    from statement_export.pipeline import run

    result = run(candidates=[], store=store, through=through, dry_run=True)
    return [(entry.notes, entry.amount) for entry in result.to_write]


def test_a_rule_added_in_the_dashboard_is_expanded_by_the_next_statement_export_run(running_server):
    store, server = running_server

    call(server, "POST", "/api/recurring-rules", WEEKLY_PAYLOAD)

    # Weekly from Wednesday 2026-08-05, so two occurrences through the 12th.
    assert expanded_notes_and_amounts(store, date(2026, 8, 12)) == [
        ("Streaming service", 100.0),
        ("Streaming service", 100.0),
    ]


def test_editing_a_rule_in_the_dashboard_changes_what_the_next_run_expands(running_server):
    store, server = running_server
    _status, created = call(server, "POST", "/api/recurring-rules", WEEKLY_PAYLOAD)

    call(server, "PUT", f"/api/recurring-rules/{created['id']}", {**WEEKLY_PAYLOAD, "amount": 150.0})

    assert expanded_notes_and_amounts(store, date(2026, 8, 5)) == [("Streaming service", 150.0)]


def test_deleting_a_rule_in_the_dashboard_stops_the_next_run_expanding_it(running_server):
    store, server = running_server
    _status, created = call(server, "POST", "/api/recurring-rules", WEEKLY_PAYLOAD)

    call(server, "DELETE", f"/api/recurring-rules/{created['id']}")

    assert expanded_notes_and_amounts(store, date(2026, 8, 12)) == []
