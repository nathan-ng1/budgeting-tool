from datetime import date

import pytest

from transaction_log.entries import ExistingRow
from transaction_log.sheets_client import (
    DATA_START_ROW,
    FULL_DATE_COLUMN_INDEX,
    GoogleSheetsClient,
    SHEET_NAME,
    SORT_COLUMN_RANGE,
    TRANSACTION_LOG_SHEET_ID,
)

SPREADSHEET_ID = "test-spreadsheet-id"


class FakeRequest:
    def __init__(self, response):
        self._response = response

    def execute(self):
        return self._response


class FakeValues:
    def __init__(self, get_response_by_range=None):
        self._get_response_by_range = get_response_by_range or {}
        self.get_calls = []
        self.batch_update_calls = []

    def get(self, **kwargs):
        self.get_calls.append(kwargs)
        response = self._get_response_by_range.get(kwargs["range"], {})
        return FakeRequest(response)

    def batchUpdate(self, **kwargs):
        self.batch_update_calls.append(kwargs)
        return FakeRequest({})


class FakeSpreadsheets:
    def __init__(self, values, batch_update_calls):
        self._values = values
        self._batch_update_calls = batch_update_calls

    def values(self):
        return self._values

    def batchUpdate(self, **kwargs):
        self._batch_update_calls.append(kwargs)
        return FakeRequest({})


class FakeService:
    def __init__(self, get_response_by_range=None):
        self._values = FakeValues(get_response_by_range)
        self.spreadsheet_batch_update_calls = []

    def spreadsheets(self):
        return FakeSpreadsheets(self._values, self.spreadsheet_batch_update_calls)

    @property
    def values(self):
        return self._values


@pytest.fixture
def make_client():
    def _make_client(get_response_by_range=None):
        service = FakeService(get_response_by_range)
        client = GoogleSheetsClient(service=service, spreadsheet_id=SPREADSHEET_ID)
        return client, service

    return _make_client


def test_read_existing_rows_on_empty_body_returns_no_rows(make_client):
    client, _ = make_client({f"{SHEET_NAME}!C8:M": {}})

    assert client.read_existing_rows() == []


def test_read_existing_rows_skips_rows_with_no_amount(make_client):
    # A row with Category/Sub-category filled in but no Amount (e.g. the sheet's
    # built-in dropdown example row) must not be treated as a logged Transaction.
    row_missing_amount = [
        "January", 1, 46216, "", "", "", "", "Bills & Subscriptions", "", "Donations & Giving",
    ]
    client, _ = make_client({f"{SHEET_NAME}!C8:M": {"values": [row_missing_amount]}})

    assert client.read_existing_rows() == []


def test_read_existing_rows_parses_full_date_amount_and_notes(make_client):
    row = [
        "August", 5, 46239, "", 42.5, "", "", "Expenses", "", "Groceries", "Woolworths",
    ]
    client, _ = make_client({f"{SHEET_NAME}!C8:M": {"values": [row]}})

    assert client.read_existing_rows() == [
        ExistingRow(date=date(2026, 8, 5), amount=42.5, notes="Woolworths")
    ]


def test_append_rows_with_no_candidates_makes_no_api_call(make_client, make_candidate):
    client, service = make_client()

    client.append_rows([])

    assert service.values.batch_update_calls == []


def test_append_rows_writes_only_the_six_non_formula_columns_at_the_next_empty_row(
    make_client, make_candidate
):
    # Column C already has 2 filled rows below the header (rows 8-9), so the next
    # empty row is 10. Columns E/F/H/I/K hold formulas and must never be touched.
    client, service = make_client(
        {f"{SHEET_NAME}!C8:C": {"values": [["January"], ["February"]]}}
    )
    candidate = make_candidate(
        date=date(2026, 8, 5),
        amount=42.5,
        category="Expenses",
        sub_category="Groceries",
        notes="Woolworths",
    )

    client.append_rows([candidate])

    assert len(service.values.batch_update_calls) == 1
    body = service.values.batch_update_calls[0]["body"]
    ranges = {entry["range"]: entry["values"] for entry in body["data"]}
    assert ranges == {
        f"{SHEET_NAME}!C10:C10": [["August"]],
        f"{SHEET_NAME}!D10:D10": [[5]],
        f"{SHEET_NAME}!G10:G10": [[42.5]],
        f"{SHEET_NAME}!J10:J10": [["Expenses"]],
        f"{SHEET_NAME}!L10:L10": [["Groceries"]],
        f"{SHEET_NAME}!M10:M10": [["Woolworths"]],
    }


def test_append_rows_writes_amount_positive_to_two_decimal_places(make_client, make_candidate):
    client, service = make_client({f"{SHEET_NAME}!C8:C": {}})
    candidate = make_candidate(amount=42.5)

    client.append_rows([candidate])

    body = service.values.batch_update_calls[0]["body"]
    amount_values = next(e["values"] for e in body["data"] if e["range"].startswith(f"{SHEET_NAME}!G"))
    assert amount_values == [[42.5]]


def test_append_rows_writes_a_negative_source_amount_as_positive(make_client, make_candidate):
    # A raw Statement Export Transaction is negative-signed for spend (see
    # CONTEXT.md) — the writer, not the Candidate, normalises the sign.
    client, service = make_client({f"{SHEET_NAME}!C8:C": {}})
    candidate = make_candidate(amount=-42.50)

    client.append_rows([candidate])

    body = service.values.batch_update_calls[0]["body"]
    amount_values = next(e["values"] for e in body["data"] if e["range"].startswith(f"{SHEET_NAME}!G"))
    assert amount_values == [[42.5]]


def test_append_rows_sorts_the_whole_data_body_by_full_date_descending(make_client, make_candidate):
    # 3 rows already logged (rows 8-10) plus the 2 being appended now (11-12) —
    # the whole body must be re-sorted together, not just the new rows, since a
    # new row can date-fall anywhere among the existing ones.
    client, service = make_client(
        {f"{SHEET_NAME}!C8:C": {"values": [["May"], ["June"], ["July"]]}}
    )
    candidates = [make_candidate(), make_candidate()]

    client.append_rows(candidates)

    assert service.spreadsheet_batch_update_calls == [
        {
            "spreadsheetId": SPREADSHEET_ID,
            "body": {
                "requests": [
                    {
                        "sortRange": {
                            "range": {
                                "sheetId": TRANSACTION_LOG_SHEET_ID,
                                "startRowIndex": DATA_START_ROW - 1,
                                "endRowIndex": 12,
                                **SORT_COLUMN_RANGE,
                            },
                            "sortSpecs": [
                                {"dimensionIndex": FULL_DATE_COLUMN_INDEX, "sortOrder": "DESCENDING"}
                            ],
                        }
                    }
                ]
            },
        }
    ]


def test_append_rows_with_no_candidates_does_not_sort(make_client):
    client, service = make_client()

    client.append_rows([])

    assert service.spreadsheet_batch_update_calls == []
