# Google Sheets MCP connection

**Historical/reference only.** The live Transaction Log and Recurring Transactions Config now
live in a local SQLite database (`src/database/store.py`, `DATABASE_PATH` in `.env`) — see
[ADR-0005](../adr/0005-migrate-transaction-log-and-recurring-config-to-a-local-database.md). This
doc describes the retired Google Sheets connection and its footguns, kept for reference in case
Sheets is ever reused as a one-off export target.

Read/write access to the budget spreadsheet's Transaction Log is provided by
[xing5's `mcp-google-sheets`](https://github.com/xing5/mcp-google-sheets) server, connected via
a service account (not interactive OAuth).

## Configuration

Registered as a project-scoped MCP server (`claude mcp add`), pointing at a venv-installed
executable:

```json
{
  "mcpServers": {
    "google-sheets": {
      "type": "stdio",
      "command": "<repo>\\.venv\\Scripts\\mcp-google-sheets.exe",
      "args": [],
      "env": {
        "SERVICE_ACCOUNT_PATH": "<repo>\\env\\<service-account-key>.json",
        "DRIVE_FOLDER_ID": "<budget spreadsheet's parent Drive folder ID>"
      }
    }
  }
}
```

- `SERVICE_ACCOUNT_PATH` — a Google Cloud service account key JSON file, kept under `env/`
  (gitignored — never commit this file). The service account must have edit access on the
  budget spreadsheet, shared to it the same way you'd share to any other Google account.
- `DRIVE_FOLDER_ID` — scopes `list_spreadsheets`/`search_spreadsheets` to the Drive folder
  containing the budget spreadsheet, so the tool doesn't enumerate unrelated Drive content.

The deterministic write path used to be a separate connection from this MCP server
(`transaction_log.sheets_client.connect`, used by `statement_export.pipeline.run`) that talked to
the Sheets API directly rather than through MCP tools, reading `SERVICE_ACCOUNT_PATH` and
`SPREADSHEET_ID` from the environment. That module is retired as of ADR-0005 — the live pipeline
now reads/writes `DATABASE_PATH` instead, and neither `SERVICE_ACCOUNT_PATH` nor `SPREADSHEET_ID`
is required for it to run. They're still read by this MCP server's own registration above, if
you keep it configured.

## Reproducing / refreshing credentials

1. In Google Cloud Console, create (or reuse) a service account on the project backing this
   integration, and enable the Sheets API and Drive API for that project.
2. Generate a JSON key for the service account and save it under `env/` in this repo (any
   filename — it's gitignored).
3. Share the budget spreadsheet (and/or its parent Drive folder) with the service account's
   email address, with Editor access.
4. Register the MCP server pointing `SERVICE_ACCOUNT_PATH` at the key file and `DRIVE_FOLDER_ID`
   at the spreadsheet's parent folder ID (from its Drive folder URL).
5. Verify with `list_spreadsheets` (no args) — it should return the budget spreadsheet.

## Verified connection (2026-08-02)

- `list_spreadsheets` → returns exactly one spreadsheet: "Annual Budget - 2026"
  (`1BBvEsmSSUy5Vdv5LyALWnTUSSEeppvaNl09T_DLQFT4`).
- `list_sheets` on that spreadsheet includes a `Transaction Log` tab.
- Manual round-trip against `Transaction Log`: wrote a marked test row (row 9), read it back
  (including the `Full date` formula recomputing correctly from Month/Day), then cleared it back
  to blank and confirmed the row reads as empty again. No residual test data left in the sheet.

## Beem Adjustment Sub-category verified (2026-08-03)

- `Setup!F13` already listed `Beem Adjustment` under the Income column (alongside Salary/Rental in `F11:F12`) — within the `Setup!C11:R30` range the Transaction Log's per-row Sub-category filter formula reads from, so no Setup sheet edit was needed.
- Wrote `Category: Income, Sub-category: Beem Adjustment` to test row 166 (first blank row past the real data, which ends at row 164) and confirmed the row's resolved dropdown source (`U166:AN166`, driven by `T166` mirroring `J166`) resolved to `Salary, Rental, Beem Adjustment`, with the write persisting without being rejected.
- Cleared the test row back to blank and confirmed it reads empty again. No residual test data left in the sheet.

## Transaction Log column layout (as built, not as documented in CONTEXT.md)

Month, Amount, Category and Sub-category each have a **wide merged header label one column
left of the data cell** (verified via the sheet's `merges` metadata — e.g. the "Month" label
is merged across B:C, but the value goes in C). Day, Full date and Notes have **no header
merge** — their label sits directly in their own single value column, same as Day/Full date.

| Field | Column | Notes |
|---|---|---|
| Month | C | free text, e.g. `"January"` — label merged B:C |
| Day | D | number, 1–31 — unmerged, label and value share the column |
| Full date | E | formula, derived from C+D — never write directly; unmerged |
| (currency helper) | F | formula, shows "$" once Amount is filled — never write directly |
| Amount | G | positive number, 2dp — label merged F:H |
| Category | J | must match Setup sheet's dropdown list — label merged I:J |
| Sub-category | L | must match Setup sheet's dropdown list — label merged K:L |
| Notes | M | free text — unmerged, label and value share the column |

Column N is unused (blank).

This was corrected twice now: `CONTEXT.md` originally listed Sub-Category as K and Notes as L;
that was fixed to L/N based on the merge pattern holding for every field. It doesn't — Notes'
header isn't merged like Month/Amount/Category/Sub-category are, so there's no offset for it,
and the real column is M. Confirmed against the live sheet after a real write landed Notes in N
by mistake. If another field's column is ever in doubt, check the sheet's `merges` metadata
(which fields actually have a merged label) rather than assuming every field follows the same
one-column offset.

## Data validation does not follow a sort

Sub-category (L)'s dropdown is a per-row `ONE_OF_RANGE` validation rule pointing at that row's
own `U:AN` (a `FILTER`/`TRANSPOSE` formula in U, keyed off Category, that spills the row's valid
Sub-categories rightward through AN) — e.g. row 9's rule criteria is `='Transaction Log'!U9:AN9`.

Regular formulas in a sorted row get their relative references reflowed to the row's new
position — confirmed true for the helper formulas in columns T/U, which is why the dropdown's
*source list* stays correct after a sort. But the row number baked into a data validation rule's
`ONE_OF_RANGE` range string is **not** reflowed the same way: the rule moves with its row, but
the literal range inside it stays frozen to whatever row it was originally written for. After a
sort, a row's validation can end up pointing at a completely different row's list (e.g. L11
pointing at `U146:AN146`).

Category (J) is unaffected — its validation is `ONE_OF_LIST` with a fixed literal list, identical
for every row, so there's nothing for a sort to misalign.

This means any code that sorts the Transaction Log must also rebuild column L's per-row
`ONE_OF_RANGE` validation afterwards for every row in the sorted range (not just newly written
ones — existing rows get reshuffled too). `GoogleSheetsClient._sort_and_realign_validation` in
`src/transaction_log/sheets_client.py` does this in the same `batchUpdate` call as the sort
itself (requests apply in order, so the rebuild lands on the post-sort row positions).

Diagnosed via `get_sheet_data(..., include_grid_data=True)`, which — unlike `get_sheet_formulas`
— includes each cell's `dataValidation` metadata. If a dropdown/validation mismatch shows up
again, that's the tool to reach for.

## API usage vs. free-tier quotas

The round-trip test and connection verification made **12 MCP calls** against this server in
one session: 2 Drive-backed listing calls, 6 sheet reads, 4 cell writes. Google's default quotas
for both the Sheets API and Drive API are per-minute (hundreds to tens-of-thousands of requests
per minute per project/user) with no meaningful daily cap for this kind of usage — a normal
categorisation run (read the log, append a handful of rows) will use a similar handful of calls
and stay orders of magnitude under quota.
