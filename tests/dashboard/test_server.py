import json
from dataclasses import asdict
from datetime import date
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from dashboard.queries import get_annual_overview, get_month_overview


@pytest.fixture
def running_server(serve, store):
    return store, serve(store)


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


def test_annual_overview_endpoint_returns_the_same_view_model_shape_the_query_function_produces(
    running_server, make_candidate
):
    store, server = running_server
    today = date.today()
    financial_year = today.year if today.month >= 7 else today.year - 1
    store.append_rows(
        [make_candidate(date=today, amount=42.5, type="Expense", category="Groceries", notes="Woolworths")]
    )
    expected = asdict(get_annual_overview(store, year=financial_year))

    with urlopen(f"http://127.0.0.1:{server.server_port}/api/annual-overview?year={financial_year}") as response:
        assert response.status == 200
        assert response.headers["Content-Type"] == "application/json"
        body = json.loads(response.read())

    assert body == expected


def test_annual_overview_endpoint_on_a_year_with_no_transactions_returns_a_zeroed_result(running_server):
    _store, server = running_server
    today = date.today()
    financial_year = today.year if today.month >= 7 else today.year - 1

    with urlopen(f"http://127.0.0.1:{server.server_port}/api/annual-overview?year={financial_year}") as response:
        body = json.loads(response.read())

    assert body["stat_tiles"]["income"] == 0
    assert body["monthly_average"]["income"] == 0


def test_annual_overview_endpoint_missing_year_returns_400(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        urlopen(f"http://127.0.0.1:{server.server_port}/api/annual-overview")

    assert exc_info.value.code == 400


def test_annual_overview_endpoint_period_calendar_reaches_the_query_function_as_start_month_1(
    running_server, make_candidate
):
    store, server = running_server
    today = date.today()
    store.append_rows(
        [make_candidate(date=date(today.year, 1, 5), amount=100.0, type="Income", category="Salary", notes="Employer")]
    )
    expected = asdict(get_annual_overview(store, year=today.year, start_month=1))

    with urlopen(
        f"http://127.0.0.1:{server.server_port}/api/annual-overview?year={today.year}&period=calendar"
    ) as response:
        body = json.loads(response.read())

    assert body == expected


def test_annual_overview_endpoint_period_omitted_defaults_to_financial_year(running_server):
    store, server = running_server
    today = date.today()
    financial_year = today.year if today.month >= 7 else today.year - 1
    expected = asdict(get_annual_overview(store, year=financial_year))

    with urlopen(f"http://127.0.0.1:{server.server_port}/api/annual-overview?year={financial_year}") as response:
        body = json.loads(response.read())

    assert body == expected


def test_annual_overview_endpoint_invalid_period_returns_400(running_server):
    _store, server = running_server

    with pytest.raises(HTTPError) as exc_info:
        urlopen(f"http://127.0.0.1:{server.server_port}/api/annual-overview?year=2026&period=nonsense")

    assert exc_info.value.code == 400


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


def test_latest_transaction_date_endpoint_reports_the_most_recent_transaction(running_server, make_candidate):
    store, server = running_server
    store.append_rows(
        [make_candidate(date=date(2026, 7, 1)), make_candidate(date=date(2026, 8, 3))]
    )

    with urlopen(f"http://127.0.0.1:{server.server_port}/api/latest-transaction-date") as response:
        assert json.loads(response.read()) == {"date": "2026-08-03"}


def test_latest_transaction_date_endpoint_on_an_empty_log_reports_no_date(running_server):
    _store, server = running_server

    with urlopen(f"http://127.0.0.1:{server.server_port}/api/latest-transaction-date") as response:
        assert json.loads(response.read()) == {"date": None}


def test_transaction_date_range_endpoint_reports_the_earliest_and_latest_dates(running_server, make_candidate):
    store, server = running_server
    store.append_rows(
        [make_candidate(date=date(2026, 7, 1)), make_candidate(date=date(2026, 8, 3)), make_candidate(date=date(2026, 6, 15))]
    )

    with urlopen(f"http://127.0.0.1:{server.server_port}/api/transaction-date-range") as response:
        assert json.loads(response.read()) == {"earliest": "2026-06-15", "latest": "2026-08-03"}


def test_transaction_date_range_endpoint_on_an_empty_log_reports_both_null(running_server):
    _store, server = running_server

    with urlopen(f"http://127.0.0.1:{server.server_port}/api/transaction-date-range") as response:
        assert json.loads(response.read()) == {"earliest": None, "latest": None}
