"""Split savings (Goals spec section 9, ADR-0031): one total divided across
active Goals by percentage, the remainder written as a Savings-Type row. The
server computes the allocation and writes every row in one database
transaction. Exercised over real HTTP against a real LocalStore."""

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

SPLIT = "/api/goals/split"
PREVIEW = "/api/goals/split/preview"


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


def request_body(goals_and_percents, total=1000.0, remainder_category="Savings", **overrides) -> dict:
    return {
        "total": total,
        "date": "2026-10-14",
        "allocations": [{"goal_id": goal["id"], "percent": percent} for goal, percent in goals_and_percents],
        "remainder_category": remainder_category,
        **overrides,
    }


def all_transactions(store) -> list:
    return store.read_transactions()


def archive(store, goal_id: int) -> None:
    store._connection.execute("UPDATE goals SET state = 'archived' WHERE id = ?", (goal_id,))
    store._connection.commit()


def test_a_split_writes_one_contribution_per_goal_and_the_remainder_as_savings(server, store):
    japan = make_goal(server)
    car = make_goal(server, title="Car")

    status, result = call(server, "POST", SPLIT, request_body([(japan, 50), (car, 30)], total=1000.0))

    assert status == 201
    written = {(row["category"], row["goal_id"]): row for row in result["rows"]}
    assert written[("Goals", japan["id"])]["amount"] == 500.0
    assert written[("Goals", car["id"])]["amount"] == 300.0
    assert written[("Savings", None)]["amount"] == 200.0
    assert {row["type"] for row in result["rows"]} == {"Savings"}
    assert written[("Goals", japan["id"])]["notes"] == "Japan trip"
    assert len(all_transactions(store)) == 3
    assert {t.date for t in all_transactions(store)} == {date(2026, 10, 14)}


def test_the_remainder_can_go_to_investments(server):
    japan = make_goal(server)

    _, result = call(server, "POST", SPLIT, request_body([(japan, 25)], remainder_category="Investments"))

    remainder = next(row for row in result["rows"] if row["goal_id"] is None)
    assert remainder["category"] == "Investments"
    assert remainder["amount"] == 750.0


def test_the_remainder_note_is_distinct_from_the_goal_notes(server):
    japan = make_goal(server)

    _, result = call(server, "POST", SPLIT, request_body([(japan, 25)]))

    notes = [row["notes"] for row in result["rows"]]
    assert len(set(notes)) == len(notes)


def test_goals_taking_exactly_one_hundred_percent_write_no_remainder_row(server, store):
    japan = make_goal(server)
    car = make_goal(server, title="Car")

    _, result = call(server, "POST", SPLIT, request_body([(japan, 60), (car, 40)]))

    assert [row["category"] for row in result["rows"]] == ["Goals", "Goals"]
    assert len(all_transactions(store)) == 2


def test_a_goal_with_a_zero_share_gets_no_row(server):
    japan = make_goal(server)
    car = make_goal(server, title="Car")

    _, result = call(server, "POST", SPLIT, request_body([(japan, 0), (car, 100)]))

    assert [row["goal_id"] for row in result["rows"]] == [car["id"]]


def test_the_rows_sum_exactly_to_the_total(server):
    goals = [make_goal(server, title=f"Goal {n}") for n in range(3)]

    _, result = call(server, "POST", SPLIT, request_body([(g, 33.33) for g in goals], total=1000.01))

    assert round(sum(row["amount"] for row in result["rows"]) * 100) == 100_001


def test_the_server_does_the_allocation_so_the_same_inputs_give_the_same_rows(server):
    goals = [make_goal(server, title=f"Goal {n}") for n in range(3)]
    body = request_body([(g, 33.33) for g in goals], total=1001.0)

    first = call(server, "POST", PREVIEW, body)[1]
    second = call(server, "POST", PREVIEW, body)[1]

    assert first == second


def test_a_preview_returns_exactly_the_rows_a_split_then_writes_and_writes_nothing(server, store):
    japan = make_goal(server)
    car = make_goal(server, title="Car")
    body = request_body([(japan, 33.33), (car, 33.33)], total=100.0)

    status, preview = call(server, "POST", PREVIEW, body)

    assert status == 200
    assert all_transactions(store) == []

    _, written = call(server, "POST", SPLIT, body)
    strip = lambda rows: [{k: v for k, v in row.items() if k != "id"} for row in rows]
    assert strip(written["rows"]) == strip(preview["rows"])


def test_percentages_over_one_hundred_are_refused_and_write_nothing(server, store):
    japan = make_goal(server)
    car = make_goal(server, title="Car")

    status, message = failure(server, "POST", SPLIT, request_body([(japan, 70), (car, 30.5)]))

    assert status == 400
    assert "100" in message
    assert all_transactions(store) == []


def test_the_same_inputs_twice_write_two_sets_of_rows_with_no_dedupe(server, store):
    japan = make_goal(server)
    body = request_body([(japan, 100)])

    call(server, "POST", SPLIT, body)
    call(server, "POST", SPLIT, body)

    assert len(all_transactions(store)) == 2


def test_a_failure_part_way_writes_none_of_the_rows(server, store):
    japan = make_goal(server)
    car = make_goal(server, title="Car")
    # Make the second INSERT fail, after the first has gone in.
    store._connection.execute(
        "CREATE TRIGGER fail_second BEFORE INSERT ON transactions "
        "WHEN (SELECT COUNT(*) FROM transactions) >= 1 BEGIN SELECT RAISE(ABORT, 'boom'); END"
    )

    status, _ = failure(server, "POST", SPLIT, request_body([(japan, 50), (car, 50)]))

    assert status == 500
    store._connection.execute("DROP TRIGGER fail_second")
    assert all_transactions(store) == []


def test_a_split_onto_an_inactive_goal_is_refused_and_writes_nothing(server, store):
    japan = make_goal(server)
    car = make_goal(server, title="Car")
    archive(store, car["id"])

    status, message = failure(server, "POST", SPLIT, request_body([(japan, 50), (car, 50)]))

    assert status == 400
    assert "active" in message
    assert all_transactions(store) == []


def test_a_preview_also_refuses_an_inactive_goal(server, store):
    japan = make_goal(server)
    archive(store, japan["id"])

    status, _ = failure(server, "POST", PREVIEW, request_body([(japan, 50)]))

    assert status == 400


def test_a_split_onto_a_missing_goal_is_refused(server):
    status, message = failure(server, "POST", SPLIT, request_body([({"id": 999}, 50)]))

    assert status == 400
    assert "999" in message


@pytest.mark.parametrize(
    "overrides",
    [
        {"total": 0},
        {"total": -5},
        {"total": "lots"},
        {"date": "yesterday"},
        {"remainder_category": "Groceries"},
        {"remainder_category": "Goals"},
        {"allocations": [{"goal_id": 1, "percent": -5}]},
    ],
)
def test_unusable_input_is_a_400(server, overrides):
    make_goal(server)

    status, _ = failure(server, "POST", SPLIT, request_body([({"id": 1}, 50)], **overrides))

    assert status == 400


def test_a_total_with_fractions_of_a_cent_is_rounded_to_the_cent(server):
    japan = make_goal(server)

    status, body = call(server, "POST", SPLIT, request_body([(japan, 100)], total=10.006))

    assert status == 201
    assert [row["amount"] for row in body["rows"]] == [10.01]


def test_a_goal_may_appear_only_once(server):
    japan = make_goal(server)

    status, _ = failure(server, "POST", SPLIT, request_body([(japan, 30), (japan, 30)]))

    assert status == 400


def test_the_splits_contributions_count_toward_each_goals_saved(server):
    japan = make_goal(server)
    call(server, "POST", SPLIT, request_body([(japan, 50)], total=800.0))

    listing = call(server, "GET", "/api/goals")[1]

    assert listing["goals"][0]["saved"] == 400.0
