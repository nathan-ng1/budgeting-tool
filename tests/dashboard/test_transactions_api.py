"""The Transactions tab's read and CRUD endpoints (Issues #33 and #35).

Exercised over real HTTP against a real LocalStore, mirroring
tests/dashboard/test_recurring_api.py - a test failing here means the
Dashboard's Transactions tab would fail the same way.
"""

import json
from datetime import date
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

PAYLOAD = {
    "date": "2026-08-05",
    "amount": 42.5,
    "type": "Expense",
    "category": "Groceries",
    "notes": "Woolworths",
}


@pytest.fixture
def running_server(serve, store):
    return store, serve(store)


def get(server, path: str):
    with urlopen(f"http://127.0.0.1:{server.server_port}{path}") as response:
        return response.status, json.loads(response.read())


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


def test_creating_a_transaction_returns_it_with_the_id_the_store_gave_it(running_server):
    _store, server = running_server

    status, created = call(server, "POST", "/api/transactions", PAYLOAD)

    assert status == 201
    assert created["id"] is not None
    assert {key: created[key] for key in PAYLOAD} == PAYLOAD


def test_a_created_transaction_then_appears_in_the_financial_year_listing(running_server):
    _store, server = running_server
    _status, created = call(server, "POST", "/api/transactions", PAYLOAD)

    _status, listed = call(server, "GET", "/api/transactions?year=2026&month=7")

    assert listed == [created]


def test_a_transaction_created_through_the_endpoint_is_what_dedupe_reads_next(running_server):
    store, server = running_server

    call(server, "POST", "/api/transactions", PAYLOAD)

    assert [row.notes for row in store.read_existing_rows()] == ["Woolworths"]


def test_editing_a_transaction_replaces_it_in_place(running_server):
    store, server = running_server
    _status, created = call(server, "POST", "/api/transactions", PAYLOAD)

    status, updated = call(server, "PUT", f"/api/transactions/{created['id']}", {**PAYLOAD, "amount": 50.0})

    assert status == 200
    assert updated["id"] == created["id"]
    assert updated["amount"] == 50.0
    assert [t.amount for t in store.read_transactions()] == [50.0]


def test_deleting_a_transaction_removes_it_from_the_listing(running_server):
    store, server = running_server
    _status, created = call(server, "POST", "/api/transactions", PAYLOAD)

    status, _body = call(server, "DELETE", f"/api/transactions/{created['id']}")

    assert status == 204
    assert call(server, "GET", "/api/transactions?year=2026&month=7")[1] == []
    assert store.read_transactions() == []


def test_creating_a_transaction_with_an_invalid_type_category_pair_is_rejected(running_server):
    store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "POST", "/api/transactions", {**PAYLOAD, "category": "Salary"})

    assert exc_info.value.code == 400
    assert "Salary" in json.loads(exc_info.value.read())["error"]
    assert store.read_transactions() == []


def test_creating_a_transaction_with_a_zero_amount_is_rejected(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "POST", "/api/transactions", {**PAYLOAD, "amount": 0})

    assert exc_info.value.code == 400


def test_editing_a_transaction_into_an_invalid_pair_is_rejected_and_leaves_it_alone(running_server):
    store, server = running_server
    _status, created = call(server, "POST", "/api/transactions", PAYLOAD)

    with pytest.raises(HTTPError) as exc_info:
        call(server, "PUT", f"/api/transactions/{created['id']}", {**PAYLOAD, "category": "Salary"})

    assert exc_info.value.code == 400
    assert [t.category for t in store.read_transactions()] == ["Groceries"]


def test_a_payload_missing_a_field_is_rejected_with_a_clear_error(running_server):
    _store, server = running_server
    incomplete = {key: value for key, value in PAYLOAD.items() if key != "date"}

    with pytest.raises(HTTPError) as exc_info:
        call(server, "POST", "/api/transactions", incomplete)

    assert exc_info.value.code == 400
    assert "date" in json.loads(exc_info.value.read())["error"]


def test_a_body_that_is_not_json_is_rejected(running_server):
    _store, server = running_server
    request = Request(
        f"http://127.0.0.1:{server.server_port}/api/transactions",
        data=b"not json at all",
        method="POST",
    )

    with pytest.raises(HTTPError) as exc_info:
        urlopen(request)

    assert exc_info.value.code == 400


def test_editing_a_transaction_that_does_not_exist_returns_404(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "PUT", "/api/transactions/404", PAYLOAD)

    assert exc_info.value.code == 404


def test_deleting_a_transaction_that_does_not_exist_returns_404(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "DELETE", "/api/transactions/404")

    assert exc_info.value.code == 404


def test_a_non_numeric_transaction_id_returns_404(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        call(server, "DELETE", "/api/transactions/not-a-number")

    assert exc_info.value.code == 404


def get_csv(server, path: str):
    with urlopen(f"http://127.0.0.1:{server.server_port}{path}") as response:
        return response.status, response.headers, response.read().decode("utf-8")


def test_export_on_an_empty_range_returns_a_header_only_csv(running_server):
    _store, server = running_server

    status, _headers, body = get_csv(server, "/api/transactions/export?start=2026-08-01&end=2026-08-31")

    assert status == 200
    assert body == "Date,Amount,Type,Category,Notes\r\n"


def test_export_has_exactly_five_columns_and_no_id(running_server):
    _store, server = running_server
    call(server, "POST", "/api/transactions", PAYLOAD)

    _status, _headers, body = get_csv(server, "/api/transactions/export?start=2026-08-01&end=2026-08-31")

    lines = body.strip("\r\n").split("\r\n")
    assert lines[0] == "Date,Amount,Type,Category,Notes"
    assert lines[1] == "2026-08-05,42.5,Expense,Groceries,Woolworths"


def test_export_bounds_are_inclusive(running_server, make_candidate):
    store, server = running_server
    store.append_rows(
        [
            make_candidate(date=date(2026, 7, 31), notes="Before the range"),
            make_candidate(date=date(2026, 8, 1), notes="Start of the range"),
            make_candidate(date=date(2026, 8, 31), notes="End of the range"),
            make_candidate(date=date(2026, 9, 1), notes="After the range"),
        ]
    )

    _status, _headers, body = get_csv(server, "/api/transactions/export?start=2026-08-01&end=2026-08-31")

    assert "Before the range" not in body
    assert "Start of the range" in body
    assert "End of the range" in body
    assert "After the range" not in body


def test_export_spans_a_financial_year_boundary(running_server, make_candidate):
    store, server = running_server
    store.append_rows(
        [
            make_candidate(date=date(2026, 6, 30), notes="Last day of FY25-26"),
            make_candidate(date=date(2026, 7, 1), notes="First day of FY26-27"),
        ]
    )

    _status, _headers, body = get_csv(server, "/api/transactions/export?start=2026-06-30&end=2026-07-01")

    assert "Last day of FY25-26" in body
    assert "First day of FY26-27" in body


def test_export_sets_content_disposition_attachment(running_server):
    _store, server = running_server

    _status, headers, _body = get_csv(server, "/api/transactions/export?start=2026-08-01&end=2026-08-31")

    assert headers["Content-Disposition"].startswith("attachment;")
    assert ".csv" in headers["Content-Disposition"]


def test_export_missing_query_params_returns_400(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        urlopen(f"http://127.0.0.1:{server.server_port}/api/transactions/export")

    assert exc_info.value.code == 400


def test_export_malformed_date_returns_400(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        urlopen(
            f"http://127.0.0.1:{server.server_port}/api/transactions/export?start=not-a-date&end=2026-08-31"
        )

    assert exc_info.value.code == 400
