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

# The Transaction Log's non-formula columns — single source of truth for both
# the read offsets (into a row read from f"{SHEET_NAME}!{_ROW_START_COLUMN}{row}:N{row}")
# and the write targets in append_rows. Columns E/F/H/I/K/M hold live formulas
# (Full date, currency helper) or are blank spacers and must never be touched.
_ROW_START_COLUMN = "C"
FULL_DATE_COLUMN = "E"
AMOUNT_COLUMN = "G"
NOTES_COLUMN = "N"


def _offset(column: str) -> int:
    return ord(column) - ord(_ROW_START_COLUMN)


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
                range=f"{SHEET_NAME}!{_ROW_START_COLUMN}{DATA_START_ROW}:N",
                valueRenderOption="UNFORMATTED_VALUE",
            )
            .execute()
        )

        existing_rows = []
        for row in response.get("values", []):
            amount = _cell(row, _offset(AMOUNT_COLUMN))
            full_date = _cell(row, _offset(FULL_DATE_COLUMN))
            if amount in (None, "") or full_date in (None, "", "-"):
                # No Amount means this isn't a logged Transaction — e.g. the
                # sheet's built-in dropdown example row at row 8.
                continue
            notes = _cell(row, _offset(NOTES_COLUMN))
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
            "C": [MONTH_NAMES[c.date.month - 1] for c in candidates],
            "D": [c.date.day for c in candidates],
            AMOUNT_COLUMN: [round(abs(c.amount), 2) for c in candidates],
            "J": [c.category for c in candidates],
            "L": [c.sub_category for c in candidates],
            NOTES_COLUMN: [c.notes for c in candidates],
        }
        data = [
            {"range": f"{SHEET_NAME}!{column}{start_row}:{column}{end_row}", "values": [[v] for v in values]}
            for column, values in columns.items()
        ]

        self._values().batchUpdate(
            spreadsheetId=self._spreadsheet_id,
            body={"valueInputOption": "USER_ENTERED", "data": data},
        ).execute()

    def _next_empty_row(self) -> int:
        response = (
            self._values()
            .get(spreadsheetId=self._spreadsheet_id, range=f"{SHEET_NAME}!{_ROW_START_COLUMN}{DATA_START_ROW}:C")
            .execute()
        )
        filled_rows = len(response.get("values", []))
        return DATA_START_ROW + filled_rows

    def _values(self):
        return self._service.spreadsheets().values()


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
