"""Archive, delete, Past goals and reactivate (Goals spec section 7.1, ADR-0031),
exercised over real HTTP against a real LocalStore."""

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
        return response.status, json.loads(response.read())


def failure(server, method: str, path: str, payload: dict | None = None):
    with pytest.raises(HTTPError) as caught:
        call(server, method, path, payload)
    return caught.value.code, json.loads(caught.value.read())["error"]


@pytest.mark.parametrize("action, state", [("archive", "archived"), ("delete", "deleted")])
def test_archiving_or_deleting_a_goal_moves_it_to_past_goals_with_its_state(server, action, state):
    _, kept = call(server, "POST", "/api/goals", {**JAPAN, "title": "Kept"})
    _, goal = call(server, "POST", "/api/goals", JAPAN)

    status, body = call(server, "POST", f"/api/goals/{goal['id']}/{action}")

    assert status == 200
    assert body["state"] == state
    _, listing = call(server, "GET", "/api/goals")
    assert [g["id"] for g in listing["goals"]] == [kept["id"]]
    assert [(g["id"], g["state"]) for g in listing["past"]] == [(goal["id"], state)]


def test_archiving_or_deleting_an_unknown_goal_is_404(server):
    assert failure(server, "POST", "/api/goals/999/archive")[0] == 404
    assert failure(server, "POST", "/api/goals/999/delete")[0] == 404


def test_a_past_goal_still_counts_its_contributions_toward_saved(server):
    _, goal = call(server, "POST", "/api/goals", JAPAN)
    call(server, "POST", f"/api/goals/{goal['id']}/contributions", {"amount": 300, "date": "2026-10-01"})

    call(server, "POST", f"/api/goals/{goal['id']}/archive")

    _, listing = call(server, "GET", "/api/goals")
    assert listing["past"][0]["saved"] == 300


def test_a_past_goal_takes_no_new_contribution(server):
    _, goal = call(server, "POST", "/api/goals", JAPAN)
    call(server, "POST", f"/api/goals/{goal['id']}/delete")

    code, _ = failure(server, "POST", f"/api/goals/{goal['id']}/contributions", {"amount": 5, "date": "2026-10-01"})

    assert code == 400


def test_a_past_goal_keeps_its_title_reserved(server):
    _, goal = call(server, "POST", "/api/goals", JAPAN)
    call(server, "POST", f"/api/goals/{goal['id']}/archive")

    assert failure(server, "POST", "/api/goals", JAPAN)[0] == 400


def test_saving_a_past_goal_with_state_active_reactivates_it_and_extends_its_dates(server):
    _, goal = call(server, "POST", "/api/goals", JAPAN)
    call(server, "POST", f"/api/goals/{goal['id']}/archive")

    status, body = call(
        server, "PUT", f"/api/goals/{goal['id']}", {**JAPAN, "end_date": "2027-09-30", "state": "active"}
    )

    assert status == 200
    assert body["state"] == "active"
    assert body["end_date"] == "2027-09-30"
    _, listing = call(server, "GET", "/api/goals")
    assert [g["id"] for g in listing["goals"]] == [goal["id"]]
    assert listing["past"] == []


def test_a_plain_edit_of_a_past_goal_leaves_it_past(server):
    _, goal = call(server, "POST", "/api/goals", JAPAN)
    call(server, "POST", f"/api/goals/{goal['id']}/delete")

    _, body = call(server, "PUT", f"/api/goals/{goal['id']}", {**JAPAN, "target_amount": 7000.0})

    assert body["state"] == "deleted"


def test_only_active_is_accepted_as_a_state_on_edit(server):
    _, goal = call(server, "POST", "/api/goals", JAPAN)

    code, _ = failure(server, "PUT", f"/api/goals/{goal['id']}", {**JAPAN, "state": "archived"})

    assert code == 400


def test_a_contribution_row_reports_its_goals_state(server):
    _, goal = call(server, "POST", "/api/goals", JAPAN)
    call(server, "POST", f"/api/goals/{goal['id']}/contributions", {"amount": 50, "date": "2026-10-01"})
    call(server, "POST", f"/api/goals/{goal['id']}/delete")

    _, rows = call(server, "GET", "/api/transactions?year=2026&month=7")

    assert [(r["goal_title"], r["goal_state"]) for r in rows] == [("Japan trip", "deleted")]
