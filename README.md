# Budgeting Tool

A personal, manually-triggered process that turns credit card statement exports into
categorised entries in a Google Sheets budget ("Annual Budget - 2026").

See `CONTEXT.md` for the full glossary of terms used below (Statement Export, Sanitising,
Transaction Log, Needs Review, Recurring Transaction, etc).

## How it works, in short

1. You download a **Statement Export** (a raw CSV) from your card issuer's online banking into
   a local Transactions Inbox.
2. A script **sanitises** it — strips personal identifiers — and moves it into `.data/`.
3. You ask Claude to process it. Claude parses the export, assigns a Category/Sub-category to
   each transaction, asks you to resolve anything it isn't confident about (**Needs Review**),
   then writes the categorised transactions to the **Transaction Log** tab of your Google Sheet
   via an MCP connection, and archives the source file.
4. Recurring items (salary, rent, mortgage, subscriptions, etc.) are expanded from a config file
   and written the same way, with or without a new export present.

There is no dry-run mode — writes land in your real spreadsheet.

## One-time setup

### 1. Install dependencies

This project uses [`uv`](https://docs.astral.sh/uv/) and Python 3.12+.

```
uv sync --extra mcp
```

### 2. Google Cloud service account

Read/write access to the spreadsheet goes through a Google service account, not interactive
OAuth login.

1. In Google Cloud Console, create (or reuse) a service account on a project with the **Sheets
   API** and **Drive API** enabled.
2. Generate a JSON key for the service account and save it under `env/` in this repo (any
   filename — `env/` is gitignored, so it never gets committed).
3. Share your budget spreadsheet (and/or its parent Drive folder) with the service account's
   email address, giving it **Editor** access — the same way you'd share it with any other
   Google account.

### 3. Register the Google Sheets MCP server

Add an MCP server entry (e.g. via `claude mcp add`, project-scoped) pointing at the
venv-installed executable:

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

- `SERVICE_ACCOUNT_PATH` — path to the key file from step 2.
- `DRIVE_FOLDER_ID` — the Drive folder ID containing your budget spreadsheet (from its folder's
  URL), so the MCP server's listing tools don't enumerate unrelated Drive content.

Verify the connection by asking Claude to call `list_spreadsheets` — it should return exactly
your budget spreadsheet. Full details, including the verified Transaction Log column layout, are
in `docs/agents/google-sheets-mcp.md`.

### 4. Set up the recurring transactions config (optional)

If you have predictable recurring items (salary, rent, mortgage, subscriptions), fill out
`config/recurring-transactions.xlsx` — one row per rule (amount, category, sub-category, notes,
frequency/interval/day, start/end date). This file is gitignored since it holds real financial
figures.

## Day-to-day usage

### Processing a new Statement Export

1. **Download** the export unchanged into the Transactions Inbox (a folder outside this repo —
   Claude never reads it directly; see
   [ADR-0001](docs/adr/0001-sanitising-happens-outside-claudes-read-access.md)). Name it
   `{Issuer}_{yyyymmdd}.csv` (e.g. `ANZ_20260830.csv`) — the issuer prefix must match a handler
   registered in `src/sanitising/sanitise.py` (currently just `ANZ`).

2. **Sanitise it yourself** (not via Claude):

   ```
   uv run python -m sanitising
   ```

   This moves every recognised export from the inbox into `.data/`, stripping personal
   identifiers per-issuer. Anything sitting directly in `.data/` afterwards is outstanding and
   hasn't been written to the Transaction Log yet.

3. **Ask Claude to process it** — e.g. "process the new statement export", in this repo. Claude
   will parse it, drop Payments & Refunds, categorise every remaining transaction, list anything
   it's unsure about as Needs Review and wait for your input, then write the deduped result to
   the live Transaction Log and archive the source file to `.data/processed/`.

Want a preview before anything is written? Ask Claude to list the categorisation first without
running the pipeline.

### Checking recurring transactions

You can ask Claude to "check for due recurring transactions" at any time, independent of a new
export — it expands `config/recurring-transactions.xlsx` through today, dedupes against the
Transaction Log, and writes what's due.

Full walkthrough: `docs/agents/statement-export-pipeline.md`.

## Repo layout

```
CONTEXT.md                 Domain glossary
docs/adr/                  Architecture decisions
docs/agents/                Agent-facing runbooks (issue tracker, MCP, pipeline)
config/recurring-transactions.xlsx   Recurring items config (gitignored)
env/                       Service account key (gitignored)
.data/                     Sanitised exports awaiting processing; .data/processed/ once written
src/sanitising/            Sanitising script (run manually)
src/statement_export/      Statement Export parsing + pipeline wiring
src/recurring/             Recurring Transactions Config expansion
src/transaction_log/       Dedupe + Google Sheets writer
tests/                     pytest suite
```

## Running tests

```
uv run pytest
```
