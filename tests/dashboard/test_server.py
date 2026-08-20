import json
import threading
from dataclasses import asdict
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from dashboard.queries import get_month_overview
from dashboard.server import build_server
from database.store import connect


@pytest.fixture
def running_server(tmp_path: Path):
    store = connect(tmp_path / "budget.db")
    server = build_server(store)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield store, server
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_overview_endpoint_returns_the_same_view_model_shape_the_query_function_produces(
    running_server, make_candidate
):
    store, server = running_server
    store.append_rows(
        [
            make_candidate(date=date(2026, 8, 5), amount=42.5, type="Expense", category="Groceries", notes="Woolworths"),
            make_candidate(date=date(2026, 8, 6), amount=4000.0, type="Income", category="Salary", notes="Employer"),
        ]
    )
    expected = asdict(get_month_overview(store, year=2026, month=8))

    with urlopen(f"http://127.0.0.1:{server.server_port}/api/overview?year=2026&month=8") as response:
        assert response.status == 200
        assert response.headers["Content-Type"] == "application/json"
        body = json.loads(response.read())

    assert body == expected


def test_overview_endpoint_on_a_month_with_no_transactions_returns_a_zeroed_result(running_server):
    _store, server = running_server

    with urlopen(f"http://127.0.0.1:{server.server_port}/api/overview?year=2026&month=8") as response:
        body = json.loads(response.read())

    assert body["stat_tiles"]["income"] == 0
    assert body["stat_tiles"]["expenses"] == 0
    assert body["spending_by_category"] == []


def test_unknown_path_returns_404(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        urlopen(f"http://127.0.0.1:{server.server_port}/api/unknown")

    assert exc_info.value.code == 404


def test_missing_query_params_returns_400(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        urlopen(f"http://127.0.0.1:{server.server_port}/api/overview")

    assert exc_info.value.code == 400


def test_server_binds_to_localhost_only_by_default(running_server):
    _store, server = running_server

    assert server.server_address[0] == "127.0.0.1"
