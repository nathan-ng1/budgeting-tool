# Google Sheets MCP connection

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

## API usage vs. free-tier quotas

The round-trip test and connection verification made **12 MCP calls** against this server in
one session: 2 Drive-backed listing calls, 6 sheet reads, 4 cell writes. Google's default quotas
for both the Sheets API and Drive API are per-minute (hundreds to tens-of-thousands of requests
per minute per project/user) with no meaningful daily cap for this kind of usage — a normal
categorisation run (read the log, append a handful of rows) will use a similar handful of calls
and stay orders of magnitude under quota.
