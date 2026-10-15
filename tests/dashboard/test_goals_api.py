"""The Goals endpoint (Goals spec section 7), exercised over real HTTP against
a real LocalStore. "Today" is injected so every figure is deterministic."""

import json
from datetime import date
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

TODAY = date(2026, 10, 14)

JAPAN = {
    "title": "Japan trip",
    "description": "Flights and a rail pass",
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


def test_a_fresh_database_has_no_goals_and_reports_the_single_today(server):
    status, body = call(server, "GET", "/api/goals")

    assert status == 200
    assert body == {"today": "2026-10-14", "goals": [], "past": []}


def test_a_created_goal_is_returned_with_its_fields_and_listed(server):
    status, created = call(server, "POST", "/api/goals", JAPAN)

    assert status == 201
    assert created["id"] >= 1
    assert created["title"] == "Japan trip"
    assert created["description"] == "Flights and a rail pass"
    assert created["target_amount"] == 6000.0
    assert created["start_date"] == "2026-07-01"
    assert created["end_date"] == "2027-03-31"
    assert created["state"] == "active"
    assert created["saved"] == 0

    _, listing = call(server, "GET", "/api/goals")
    assert [goal["id"] for goal in listing["goals"]] == [created["id"]]


def test_a_blank_description_is_stored_as_none_and_text_is_trimmed(server):
    _, created = call(server, "POST", "/api/goals", {**JAPAN, "title": "  Japan trip  ", "description": "   "})

    assert created["title"] == "Japan trip"
    assert created["description"] is None


def test_the_description_is_optional(server):
    payload = {key: value for key, value in JAPAN.items() if key != "description"}

    status, created = call(server, "POST", "/api/goals", payload)

    assert status == 201
    assert created["description"] is None


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"title": "   "}, "title"),
        ({"target_amount": 0}, "above zero"),
        ({"target_amount": -5}, "above zero"),
        ({"target_amount": "lots"}, "number"),
        ({"end_date": "2026-06-30"}, "end date"),
        ({"end_date": "not a date"}, "end_date"),
        ({"start_date": None}, "start_date"),
    ],
)
def test_an_invalid_goal_is_refused_with_400(server, change, message):
    code, error = failure(server, "POST", "/api/goals", {**JAPAN, **change})

    assert code == 400
    assert message in error

    _, listing = call(server, "GET", "/api/goals")
    assert listing["goals"] == []


def test_a_missing_required_field_is_refused_with_400(server):
    payload = {key: value for key, value in JAPAN.items() if key != "end_date"}

    code, error = failure(server, "POST", "/api/goals", payload)

    assert code == 400
    assert "end_date" in error


def test_an_end_date_equal_to_the_start_date_is_allowed(server):
    status, _ = call(server, "POST", "/api/goals", {**JAPAN, "start_date": "2026-12-01", "end_date": "2026-12-01"})

    assert status == 201


@pytest.mark.parametrize("title", ["japan trip", "  JAPAN TRIP ", "Japan Trip"])
def test_a_title_is_unique_ignoring_case_and_surrounding_spaces(server, title):
    call(server, "POST", "/api/goals", JAPAN)

    code, error = failure(server, "POST", "/api/goals", {**JAPAN, "title": title})

    assert code == 400
    assert "Japan trip" in error


def test_title_uniqueness_folds_beyond_ascii(server):
    call(server, "POST", "/api/goals", {**JAPAN, "title": "Straße fund"})

    code, _ = failure(server, "POST", "/api/goals", {**JAPAN, "title": "STRASSE FUND"})

    assert code == 400


def test_title_uniqueness_counts_archived_and_deleted_goals(server, store):
    for state in ("archived", "deleted"):
        _, created = call(server, "POST", "/api/goals", {**JAPAN, "title": f"Old {state}"})
        store._connection.execute("UPDATE goals SET state = ? WHERE id = ?", (state, created["id"]))
        store._connection.commit()

        code, _ = failure(server, "POST", "/api/goals", {**JAPAN, "title": f"old {state}"})

        assert code == 400


def test_archived_and_deleted_goals_are_listed_apart_from_the_active_ones(server, store):
    _, live = call(server, "POST", "/api/goals", JAPAN)
    _, old = call(server, "POST", "/api/goals", {**JAPAN, "title": "Old"})
    store._connection.execute("UPDATE goals SET state = 'archived' WHERE id = ?", (old["id"],))
    store._connection.commit()

    _, listing = call(server, "GET", "/api/goals")

    assert [goal["id"] for goal in listing["goals"]] == [live["id"]]
    assert [(goal["id"], goal["state"]) for goal in listing["past"]] == [(old["id"], "archived")]


def test_editing_a_goal_replaces_its_fields_and_keeps_its_id(server):
    _, created = call(server, "POST", "/api/goals", JAPAN)

    status, edited = call(
        server,
        "PUT",
        f"/api/goals/{created['id']}",
        {**JAPAN, "title": "Japan 2027", "target_amount": 7000.0, "end_date": "2027-04-30"},
    )

    assert status == 200
    assert edited["id"] == created["id"]
    assert edited["title"] == "Japan 2027"
    assert edited["target_amount"] == 7000.0
    assert edited["end_date"] == "2027-04-30"
    _, listing = call(server, "GET", "/api/goals")
    assert [goal["title"] for goal in listing["goals"]] == ["Japan 2027"]


def test_a_goal_can_be_saved_under_its_own_title(server):
    _, created = call(server, "POST", "/api/goals", JAPAN)

    status, _ = call(server, "PUT", f"/api/goals/{created['id']}", {**JAPAN, "title": "JAPAN TRIP"})

    assert status == 200


def test_editing_cannot_take_another_goals_title(server):
    call(server, "POST", "/api/goals", JAPAN)
    _, other = call(server, "POST", "/api/goals", {**JAPAN, "title": "Car"})

    code, _ = failure(server, "PUT", f"/api/goals/{other['id']}", {**JAPAN, "title": "japan trip"})

    assert code == 400


def test_editing_an_invalid_goal_is_refused_and_changes_nothing(server):
    _, created = call(server, "POST", "/api/goals", JAPAN)

    code, _ = failure(server, "PUT", f"/api/goals/{created['id']}", {**JAPAN, "target_amount": 0})

    assert code == 400
    _, listing = call(server, "GET", "/api/goals")
    assert listing["goals"][0]["target_amount"] == 6000.0


def test_editing_an_unknown_goal_is_404(server):
    code, _ = failure(server, "PUT", "/api/goals/999", JAPAN)

    assert code == 404


def test_the_endpoint_returns_each_goals_derived_figures_against_today(server):
    # 2026-07-01 to 2027-03-31: 8 months and 30 days = 9 months, 273 days. Today is day 105.
    _, goal = call(server, "POST", "/api/goals", JAPAN)

    assert goal["status"] == "Active"
    assert goal["flag"] == "Behind"
    assert goal["on_track"] is False
    assert goal["saved"] == 0
    assert goal["remaining"] == 6000.0
    assert goal["fraction"] == 0.0
    assert goal["months_left"] == 6  # 16 Oct 2026 to 31 Mar 2027: 5 months and 15 days
    assert goal["required_per_month"] == pytest.approx(1000.0)
    assert goal["original_plan_per_month"] == pytest.approx(6000.0 / 9)
    assert goal["pace_fraction"] == pytest.approx(105 / 273)
    assert goal["pace_amount"] == pytest.approx(6000.0 * 105 / 273)


def test_an_upcoming_goal_is_reported_upcoming(server):
    _, goal = call(server, "POST", "/api/goals", {**JAPAN, "start_date": "2026-12-01"})

    assert goal["status"] == "Upcoming"
    assert goal["pace_fraction"] == 0.0
    assert goal["on_track"] is True


def test_an_ended_goal_stays_in_the_main_list(server):
    call(server, "POST", "/api/goals", {**JAPAN, "start_date": "2025-01-01", "end_date": "2026-01-01"})

    _, listing = call(server, "GET", "/api/goals")

    assert [goal["status"] for goal in listing["goals"]] == ["Ended"]
    assert listing["goals"][0]["required_per_month"] is None
