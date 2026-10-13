"""Deleting all data and resetting the Dashboard, over real HTTP (Issue #201,
ADR-0030). Everything lives under pytest's temporary folder."""

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from datetime import date

from database.store import connect
from transaction_log.entries import Candidate


def call(server, method: str, path: str, payload=None):
    body = None if payload is None else json.dumps(payload).encode()
    request = Request(f"http://127.0.0.1:{server.server_port}{path}", data=body, method=method)
    with urlopen(request) as response:
        return response.status, json.loads(response.read())


def failure(server, method: str, path: str, payload=None):
    with pytest.raises(HTTPError) as caught:
        call(server, method, path, payload)
    return caught.value.code, json.loads(caught.value.read())["error"]


@pytest.fixture
def home(tmp_path: Path):
    """A Database with data, two pre-migration copies beside it, and bystander
    files that must survive: a Processed archive and a Transactions Inbox."""
    folder = tmp_path / "data"
    folder.mkdir()
    store = connect(folder / "budget.db")
    store.append_rows([Candidate(date=date(2026, 1, 5), amount=12.5, type="Expense", category="Groceries", notes="a")])
    store.create_category("Expense", "Hobbies", None)
    store.upsert_category_budget("Expense", "Groceries", 2026, 1, 100.0)
    store.write_settings({"currency": "GBP", "date_order": "month-first"})
    (folder / "budget.pre-migration-20260101-000000.db").write_bytes(b"old")
    (folder / "budget.pre-migration-20260102-000000.db").write_bytes(b"older")
    processed = tmp_path / "Processed"
    processed.mkdir()
    (processed / "statement.csv").write_text("keep me")
    inbox = tmp_path / "Inbox"
    inbox.mkdir()
    (inbox / "new.csv").write_text("keep me too")
    (folder / "notes.txt").write_text("not a database file")
    return folder, store, processed, inbox


def test_the_summary_reports_live_counts_the_path_and_the_pre_migration_files(serve, home):
    folder, store, _, _ = home
    server = serve(store)

    status, body = call(server, "GET", "/api/database/reset-summary")

    assert status == 200
    assert body["path"] == str((folder / "budget.db").resolve())
    assert body["pre_migration_files"] == 2
    assert body["transactions"] == 1
    assert body["recurring_rules"] == 0
    assert body["category_budgets"] == 1
    assert body["custom_categories"] == 1
    assert body["display_settings"] == 2


@pytest.mark.parametrize(
    "payload", [None, {}, {"confirmation": "delete"}, {"confirmation": "yes"}, {"confirmation": None}]
)
def test_a_reset_without_the_exact_confirmation_is_refused_and_deletes_nothing(serve, home, payload):
    folder, store, _, _ = home
    server = serve(store)

    status, _ = failure(server, "POST", "/api/database/reset", payload)

    assert status == 400
    assert (folder / "budget.pre-migration-20260101-000000.db").exists()
    assert (folder / "budget.pre-migration-20260102-000000.db").exists()
    _, summary = call(server, "GET", "/api/database/reset-summary")
    assert summary["transactions"] == 1
    assert summary["custom_categories"] == 1


def test_a_confirmed_reset_serves_a_fresh_empty_database_at_the_same_path_without_a_restart(serve, home):
    folder, store, _, _ = home
    server = serve(store)

    status, body = call(server, "POST", "/api/database/reset", {"confirmation": "DELETE"})

    assert status == 200
    assert body["path"] == str((folder / "budget.db").resolve())
    assert (folder / "budget.db").exists()
    _, summary = call(server, "GET", "/api/database/reset-summary")
    assert summary["transactions"] == 0
    assert summary["custom_categories"] == 0
    assert summary["display_settings"] == 0
    assert summary["pre_migration_files"] == 0
    _, categories = call(server, "GET", "/api/categories")
    assert any(c["name"] == "Groceries" for c in categories)  # default Categories seeded
    _, saved = call(server, "GET", "/api/settings")
    assert saved["currency"] == "AUD"
    # The fresh Database is writable straight away.
    status, _ = call(
        server,
        "POST",
        "/api/transactions",
        {"date": "2026-02-01", "amount": 3, "type": "Expense", "category": "Groceries", "notes": "x"},
    )
    assert status == 201


def test_a_confirmed_reset_removes_pre_migration_files_but_nothing_outside_the_database(serve, home):
    folder, store, processed, inbox = home
    server = serve(store)

    call(server, "POST", "/api/database/reset", {"confirmation": "DELETE"})

    assert not list(folder.glob("*.pre-migration-*.db"))
    assert (folder / "notes.txt").read_text() == "not a database file"
    assert (processed / "statement.csv").read_text() == "keep me"
    assert (inbox / "new.csv").read_text() == "keep me too"
