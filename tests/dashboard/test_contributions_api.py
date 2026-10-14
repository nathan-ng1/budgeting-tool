"""Contributions (Goals spec sections 4 and 8, ADR-0031): Goals-Category Savings
Transactions linked to a Goal, exercised over real HTTP against a real
LocalStore. The Goal-link rules are enforced by the store, so they are also
driven through the plain Transactions endpoints."""

import json
from datetime import date
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

TODAY = date(2026, 10, 14)

JAPAN = {
    "title": "Japan trip",
    "description": None,
    "target_amount": 6000.0,
    "start_date": "2026-07-01",
    "end_date": "2027-03-31",
}


@pytest.fixture
def server(serve, store):
    return serve(store, today=lambda: TODAY)


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


def failure(server, method: str, path: str, payload: dict | None = None):
    with pytest.raises(HTTPError) as caught:
        call(server, method, path, payload)
    return caught.value.code, json.loads(caught.value.read())["error"]


def make_goal(server, **overrides) -> dict:
    return call(server, "POST", "/api/goals", {**JAPAN, **overrides})[1]


def goal_transaction(goal_id, **overrides) -> dict:
    return {
        "date": "2026-10-01",
        "amount": 250.0,
        "type": "Savings",
        "category": "Goals",
        "notes": "Top-up",
        "goal_id": goal_id,
        **overrides,
    }


def goal_by_id(server, goal_id: int) -> dict:
    listing = call(server, "GET", "/api/goals")[1]
    return next(goal for goal in [*listing["goals"], *listing["past"]] if goal["id"] == goal_id)


def archive(store, goal_id: int) -> None:
    store._connection.execute("UPDATE goals SET state = 'archived' WHERE id = ?", (goal_id,))
    store._connection.commit()


def test_adding_a_contribution_writes_a_goals_savings_transaction_linked_to_the_goal(server):
    goal = make_goal(server)

    status, created = call(
        server,
        "POST",
        f"/api/goals/{goal['id']}/contributions",
        {"amount": 500.0, "date": "2026-10-10", "notes": "Bonus"},
    )

    assert status == 201
    assert created["type"] == "Savings"
    assert created["category"] == "Goals"
    assert created["goal_id"] == goal["id"]
    assert created["amount"] == 500.0
    assert created["date"] == "2026-10-10"
    assert created["notes"] == "Bonus"


def test_a_contribution_without_notes_defaults_them_to_the_goals_title(server):
    goal = make_goal(server)

    _, created = call(
        server, "POST", f"/api/goals/{goal['id']}/contributions", {"amount": 100.0, "date": "2026-10-10"}
    )

    assert created["notes"] == "Japan trip"


def test_a_contribution_updates_the_goals_saved_and_percent_funded(server):
    goal = make_goal(server)
    call(server, "POST", f"/api/goals/{goal['id']}/contributions", {"amount": 1500.0, "date": "2026-09-01"})
    call(server, "POST", f"/api/goals/{goal['id']}/contributions", {"amount": 1500.0, "date": "2026-10-01"})

    figures = goal_by_id(server, goal["id"])

    assert figures["saved"] == 3000.0
    assert figures["fraction"] == 0.5


def test_saved_counts_contributions_of_any_date_and_ignores_other_goals(server):
    first = make_goal(server)
    second = make_goal(server, title="Car")
    call(server, "POST", f"/api/goals/{first['id']}/contributions", {"amount": 100.0, "date": "2020-01-01"})
    call(server, "POST", f"/api/goals/{first['id']}/contributions", {"amount": 50.0, "date": "2030-01-01"})
    call(server, "POST", f"/api/goals/{second['id']}/contributions", {"amount": 70.0, "date": "2026-10-01"})

    assert goal_by_id(server, first["id"])["saved"] == 150.0
    assert goal_by_id(server, second["id"])["saved"] == 70.0


def test_a_contribution_to_a_missing_goal_is_a_404(server):
    status, _ = failure(server, "POST", "/api/goals/999/contributions", {"amount": 10.0, "date": "2026-10-01"})

    assert status == 404


def test_a_contribution_to_a_past_goal_is_rejected(server, store):
    goal = make_goal(server)
    archive(store, goal["id"])

    status, message = failure(
        server, "POST", f"/api/goals/{goal['id']}/contributions", {"amount": 10.0, "date": "2026-10-01"}
    )

    assert status == 400
    assert "active" in message


@pytest.mark.parametrize("amount", [0, -5, "lots"])
def test_a_contribution_needs_a_positive_amount(server, amount):
    goal = make_goal(server)

    status, _ = failure(
        server, "POST", f"/api/goals/{goal['id']}/contributions", {"amount": amount, "date": "2026-10-01"}
    )

    assert status == 400


def test_a_contribution_needs_a_date(server):
    goal = make_goal(server)

    status, message = failure(server, "POST", f"/api/goals/{goal['id']}/contributions", {"amount": 10.0})

    assert status == 400
    assert "date" in message


def test_the_store_rejects_a_goals_row_with_no_goal(server):
    status, message = failure(server, "POST", "/api/transactions", goal_transaction(None))

    assert status == 400
    assert "Goal" in message


def test_the_store_rejects_a_goal_link_on_any_other_category(server):
    goal = make_goal(server)

    status, _ = failure(
        server, "POST", "/api/transactions", goal_transaction(goal["id"], category="Savings")
    )

    assert status == 400


def test_the_store_rejects_a_link_to_a_goal_that_does_not_exist(server):
    status, message = failure(server, "POST", "/api/transactions", goal_transaction(999))

    assert status == 400
    assert "999" in message


def test_the_store_rejects_a_new_link_to_a_goal_that_is_not_active(server, store):
    goal = make_goal(server)
    archive(store, goal["id"])

    status, _ = failure(server, "POST", "/api/transactions", goal_transaction(goal["id"]))

    assert status == 400


def test_a_contribution_keeps_its_link_when_edited_after_its_goal_is_archived(server, store):
    goal = make_goal(server)
    _, created = call(server, "POST", "/api/transactions", goal_transaction(goal["id"]))
    archive(store, goal["id"])

    status, updated = call(
        server, "PUT", f"/api/transactions/{created['id']}", goal_transaction(goal["id"], notes="Renamed")
    )

    assert status == 200
    assert updated["notes"] == "Renamed"
    assert updated["goal_id"] == goal["id"]


def test_moving_a_contribution_to_an_archived_goal_is_rejected(server, store):
    first = make_goal(server)
    second = make_goal(server, title="Car")
    _, created = call(server, "POST", "/api/transactions", goal_transaction(first["id"]))
    archive(store, second["id"])

    status, _ = failure(
        server, "PUT", f"/api/transactions/{created['id']}", goal_transaction(second["id"])
    )

    assert status == 400


def test_moving_a_contribution_to_another_active_goal_moves_its_saved_amount(server):
    first = make_goal(server)
    second = make_goal(server, title="Car")
    _, created = call(server, "POST", "/api/transactions", goal_transaction(first["id"], amount=80.0))

    call(server, "PUT", f"/api/transactions/{created['id']}", goal_transaction(second["id"], amount=80.0))

    assert goal_by_id(server, first["id"])["saved"] == 0
    assert goal_by_id(server, second["id"])["saved"] == 80.0


def test_changing_a_row_away_from_goals_needs_the_goal_link_cleared(server):
    goal = make_goal(server)
    _, created = call(server, "POST", "/api/transactions", goal_transaction(goal["id"]))

    status, _ = failure(
        server,
        "PUT",
        f"/api/transactions/{created['id']}",
        goal_transaction(goal["id"], category="Savings"),
    )
    assert status == 400

    status, updated = call(
        server,
        "PUT",
        f"/api/transactions/{created['id']}",
        goal_transaction(None, category="Savings"),
    )
    assert status == 200
    assert updated["goal_id"] is None
    assert goal_by_id(server, goal["id"])["saved"] == 0


def test_re_pointing_a_savings_row_at_a_goal_links_it(server):
    goal = make_goal(server)
    _, created = call(
        server, "POST", "/api/transactions", goal_transaction(None, category="Savings", notes="Rainy day")
    )

    call(server, "PUT", f"/api/transactions/{created['id']}", goal_transaction(goal["id"], notes="Rainy day"))

    assert goal_by_id(server, goal["id"])["saved"] == 250.0


def test_listing_transactions_carries_the_goal_id_and_title(server):
    goal = make_goal(server)
    call(server, "POST", "/api/transactions", goal_transaction(goal["id"]))
    call(server, "POST", "/api/transactions", goal_transaction(None, category="Savings"))

    _, rows = call(server, "GET", "/api/transactions?year=2026&month=7")

    by_category = {row["category"]: row for row in rows}
    assert by_category["Goals"]["goal_id"] == goal["id"]
    assert by_category["Goals"]["goal_title"] == "Japan trip"
    assert by_category["Savings"]["goal_id"] is None
    assert by_category["Savings"]["goal_title"] is None

