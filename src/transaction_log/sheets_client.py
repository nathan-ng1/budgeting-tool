import os
from datetime import date, timedelta

from transaction_log.entries import Candidate, ExistingRow

# Same spreadsheet the Google Sheets MCP connection was verified against —
# see docs/agents/google-sheets-mcp.md.
SPREADSHEET_ID = "1BBvEsmSSUy5Vdv5LyALWnTUSSEeppvaNl09T_DLQFT4"
SHEET_NAME = "Transaction Log"
DATA_START_ROW = 8
SHEETS_EPOCH = date(1899, 12, 30)
MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# The Transaction Log's non-formula columns — single source of truth for
# every column reference below (read offsets, write targets, sort/validation
# indices). Columns not listed here (E/F/H/I/K) hold live formulas (Full date,
# currency helper) or are blank spacers and must never be touched. Month,
# Amount, Category and Sub-Category each have a wide merged header label one
# column left of their value column, but Notes' header is a single unmerged
# cell directly above M (like Day/Full date) — its value goes in M, not N
# (confirmed against the live sheet; N is unused).
COLUMN = {
    "month": "C",
    "day": "D",
    "full_date": "E",
    "amount": "G",
    "category": "J",
    "sub_category": "L",
    "notes": "M",
}
_ROW_START_COLUMN = COLUMN["month"]

# gid for the "Transaction Log" tab — stable unless the tab itself is deleted
# and recreated; re-fetch via spreadsheets().get() if this ever needs updating.
TRANSACTION_LOG_SHEET_ID = 1652281908

# Last column holding a per-row helper formula (a Setup-driven Sub-category
# lookup keyed off J). A sort must move every column through here together,
# or a helper formula ends up reading a different row's data than the row it
# now sits in after the reorder.
LAST_HELPER_COLUMN = "U"

# Sub-category (L)'s dropdown is a per-row ONE_OF_RANGE validation rule
# pointing at that row's own U:AN (the Setup-driven Sub-category list spilled
# by column U's formula) — e.g. row 9's rule reads '...!U9:AN9'. Unlike a
# regular formula, this range is a literal baked into the rule and does NOT
# get reflowed to the new row when Sheets sorts — the rule moves with its row,
# but the row number inside its range string stays frozen. So after every
# sort, every row's rule must be rebuilt by hand to point at its own row
# again. Confirmed against the live sheet: see docs/agents/google-sheets-mcp.md.
VALIDATION_SOURCE_START_COLUMN = LAST_HELPER_COLUMN
VALIDATION_SOURCE_END_COLUMN = "AN"


def _column_index(column: str) -> int:
    """0-based index from column A (e.g. "A" -> 0, "M" -> 12, "AN" -> 39)."""
    index = 0
    for char in column:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index - 1


def _offset(column: str) -> int:
    """0-based index relative to _ROW_START_COLUMN, for a row read via that range."""
    return _column_index(column) - _column_index(_ROW_START_COLUMN)


# Derived, not hand-counted, so a column move is a one-line edit to COLUMN or
# LAST_HELPER_COLUMN above rather than a hunt through separately-tracked indices.
FULL_DATE_COLUMN_INDEX = _column_index(COLUMN["full_date"])
SUB_CATEGORY_COLUMN_INDEX = _column_index(COLUMN["sub_category"])
SORT_COLUMN_RANGE = {"startColumnIndex": 0, "endColumnIndex": _column_index(LAST_HELPER_COLUMN) + 1}


class GoogleSheetsClient:
    """Live Transaction Log client, backed by the Sheets API v4.

    Mirrors FakeSheetsClient's read_existing_rows() shape (see
    tests/transaction_log/conftest.py) plus the write side the live writer needs.
    """

    def __init__(self, service, spreadsheet_id: str):
        self._service = service
        self._spreadsheet_id = spreadsheet_id

    def read_existing_rows(self) -> list[ExistingRow]:
        response = (
            self._values()
            .get(
                spreadsheetId=self._spreadsheet_id,
                range=f"{SHEET_NAME}!{_ROW_START_COLUMN}{DATA_START_ROW}:{COLUMN['notes']}",
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )

        existing_rows = []
        for row in response.get("values", []):
            amount = _cell(row, _offset(COLUMN["amount"]))
            full_date = _cell(row, _offset(COLUMN["full_date"]))
            if amount in (None, "") or full_date in (None, "", "-"):
                # No Amount means this isn't a logged Transaction — e.g. the
                # sheet's built-in dropdown example row at row 8.
                continue
            notes = _cell(row, _offset(COLUMN["notes"]))
            existing_rows.append(
                ExistingRow(
                    date=_from_serial(full_date),
                    amount=float(amount),
                    notes=str(notes) if notes else "",
                )
            )
        return existing_rows

    def append_rows(self, candidates: list[Candidate]) -> None:
        if not candidates:
            return

        start_row = self._next_empty_row()
        end_row = start_row + len(candidates) - 1

        columns = {
            COLUMN["month"]: [MONTH_NAMES[c.date.month - 1] for c in candidates],
            COLUMN["day"]: [c.date.day for c in candidates],
            COLUMN["amount"]: [round(abs(c.amount), 2) for c in candidates],
            COLUMN["category"]: [c.category for c in candidates],
            COLUMN["sub_category"]: [c.sub_category for c in candidates],
            COLUMN["notes"]: [c.notes for c in candidates],
        }
        data = [
            {"range": f"{SHEET_NAME}!{column}{start_row}:{column}{end_row}", "values": [[v] for v in values]}
            for column, values in columns.items()
        ]

        self._values().batchUpdate(
            spreadsheetId=self._spreadsheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": data},
        ).execute()

        self._sort_and_realign_validation(through_row=end_row)

    def _sort_and_realign_validation(self, through_row: int) -> None:
        sort_request = {
            "sortRange": {
                "range": {
                    "sheetId": TRANSACTION_LOG_SHEET_ID,
                    "startRowIndex": DATA_START_ROW - 1,
                    "endRowIndex": through_row,
                    **SORT_COLUMN_RANGE,
                },
                "sortSpecs": [
                    {"dimensionIndex": FULL_DATE_COLUMN_INDEX, "sortOrder": "DESCENDING"}
                ],
            }
        }
        # Requests apply in order, so this runs after the sort above and
        # rebuilds every row's Sub-category dropdown against its own (now
        # final) row position.
        validation_requests = [
            _sub_category_validation_request(row)
            for row in range(DATA_START_ROW, through_row + 1)
        ]

        self._service.spreadsheets().batchUpdate(
            spreadsheetId=self._spreadsheet_id,
            body={"requests": [sort_request, *validation_requests]},
        ).execute()

    def _next_empty_row(self) -> int:
        response = (
            self._values()
            .get(spreadsheetId=self._spreadsheet_id, range=f"{SHEET_NAME}!{_ROW_START_COLUMN}{DATA_START_ROW}:{COLUMN['month']}")
            .execute()
        )
        filled_rows = len(response.get("values", []))
        return DATA_START_ROW + filled_rows

    def _values(self):
        return self._service.spreadsheets().values()


def _sub_category_validation_request(row: int) -> dict:
    return {
        "setDataValidation": {
            "range": {
                "sheetId": TRANSACTION_LOG_SHEET_ID,
                "startRowIndex": row - 1,
                "endRowIndex": row,
                "startColumnIndex": SUB_CATEGORY_COLUMN_INDEX,
                "endColumnIndex": SUB_CATEGORY_COLUMN_INDEX + 1,
            },
            "rule": {
                "condition": {
                    "type": "ONE_OF_RANGE",
                    "values": [
                        {
                            "userEnteredValue": (
                                f"='{SHEET_NAME}'!{VALIDATION_SOURCE_START_COLUMN}{row}:"
                                f"{VALIDATION_SOURCE_END_COLUMN}{row}"
                            )
                        }
                    ],
                },
                "strict": True,
                "showCustomUi": True,
            },
        }
    }


def _cell(row: list, offset: int):
    return row[offset] if len(row) > offset else None


def _from_serial(serial: float) -> date:
    return SHEETS_EPOCH + timedelta(days=int(serial))


def connect(spreadsheet_id: str = SPREADSHEET_ID) -> GoogleSheetsClient:
    """Build a GoogleSheetsClient against the live spreadsheet.

    Uses the same service account credentials as the Google Sheets MCP
    connection (SERVICE_ACCOUNT_PATH) — see docs/agents/google-sheets-mcp.md.
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    credentials_path = os.environ["SERVICE_ACCOUNT_PATH"]
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=credentials)
    return GoogleSheetsClient(service=service, spreadsheet_id=spreadsheet_id)
