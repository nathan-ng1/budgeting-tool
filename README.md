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

## Prerequisites

- **Windows** — the day-to-day flow uses a `.bat` script and Windows-style paths by convention.
  It should work on macOS/Linux with small tweaks (a shell script instead of `.bat`,
  forward-slash paths in your `.env`), but that's untested.
- **[Claude Code](https://docs.claude.com/en/docs/claude-code)**, installed and logged in.
  **A Claude Pro/Max subscription is not required** — Claude Code also works with pay-as-you-go
  API billing through the [Anthropic Console](https://console.anthropic.com/), which is enough
  to drive this pipeline. A subscription is generally cheaper if you use Claude a lot elsewhere
  too, but isn't a requirement just for this.
- **[`uv`](https://docs.astral.sh/uv/)** and **Python 3.12+**.
- **Git**, to clone this repo.
- A **Google account** with access to Google Cloud Console, to create the service account used
  for Sheets/Drive access (step 2 below).
- Your **own budget spreadsheet** in Google Sheets with a Transaction Log tab matching the column
  layout in `docs/agents/google-sheets-mcp.md` — this repo doesn't include or provision one.
- Optional: **[GitHub CLI (`gh`)](https://cli.github.com/)**, only needed if you also want
  Claude's issue-tracker agent skill (`docs/agents/issue-tracker.md`) to file/read GitHub issues
  against your own fork/clone.

## Setting this up for someone else

Nothing personal is hardcoded in source — every per-person setting (`TRANSACTIONS_INBOX`,
`SERVICE_ACCOUNT_PATH`, `SPREADSHEET_ID`, `BEEM_USERNAME`) lives in a gitignored `.env`, copied
from `.env.example` (step 3 below). To hand this repo to someone else:

1. They clone the repo and copy their own `.env` from `.env.example` — nothing from your `.env`,
   `env/` (service account key), or `config/recurring-transactions.xlsx` should be shared, since
   those hold real financial figures/identifiers and are all gitignored for that reason.
2. **Spreadsheet + service account are per-user** — the Google Sheets MCP connection is scoped
   to a Drive folder (`DRIVE_FOLDER_ID`) expected to contain exactly one spreadsheet. Each person
   needs their own budget spreadsheet, in its own Drive folder, shared to their own Google Cloud
   service account.
3. Otherwise, they run through "One-time setup" below as-is, using their own Google Cloud
   project, service account key, spreadsheet, and MCP registration.

## One-time setup

### 1. Clone the repo and install dependencies

This project uses [`uv`](https://docs.astral.sh/uv/) and Python 3.12+.

```
git clone <this-repo-url>
cd budgeting-tool
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

### 3. Configure your `.env` file

Every per-person setting — none of them are hardcoded in source — is read from environment
variables, loaded from a `.env` file in the repo root (gitignored, so it never gets committed).
Copy the template and fill it in:

```
cp .env.example .env
```

| Variable | Required | Meaning |
|---|---|---|
| `TRANSACTIONS_INBOX` | yes | Absolute path to the folder outside this repo where you download raw Statement Exports. Read by `uv run python -m sanitising`. |
| `SERVICE_ACCOUNT_PATH` | yes | Path to the service account key JSON from step 2. Read by the write path (`transaction_log.sheets_client.connect`) — also set separately as `SERVICE_ACCOUNT_PATH` in the MCP server's own registration in step 4, since MCP config doesn't read this file. |
| `SPREADSHEET_ID` | yes | Your budget spreadsheet's ID, from its Google Sheets URL (`.../spreadsheets/d/<SPREADSHEET_ID>/edit`). Read by the write path when it connects. |
| `BEEM_USERNAME` | only for Beem reports | Which side of each row (`Payer`/`Recipient`) is you, so the Beem sanitising handler can derive a signed amount. |

Any of these also work as a real environment variable set in your shell for the session (e.g.
`$env:BEEM_USERNAME = "your_beem_username"` in PowerShell) — `.env` just saves you from setting
them every session.

### 4. Register the Google Sheets MCP server

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

- `SERVICE_ACCOUNT_PATH` — path to the key file from step 2 (same value as your `.env`, but this
  MCP registration is a separate config that doesn't read `.env`).
- `DRIVE_FOLDER_ID` — the Drive folder ID containing your budget spreadsheet (from its folder's
  URL), so the MCP server's listing tools don't enumerate unrelated Drive content.

Verify the connection by asking Claude to call `list_spreadsheets` — it should return exactly
your budget spreadsheet. Full details, including the verified Transaction Log column layout, are
in `docs/agents/google-sheets-mcp.md`.

### 5. Set up the recurring transactions config (optional)

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
   registered in `src/sanitising/sanitise.py` (currently `ANZ`, `Beem`, and `NAB`).

2. **Sanitise it yourself** (not via Claude):

   ```
   uv run python -m sanitising
   ```

   This moves every recognised export from the inbox into `.data/`, stripping personal
   identifiers per-issuer. Anything sitting directly in `.data/` afterwards is outstanding and
   hasn't been written to the Transaction Log yet.

3. **Ask Claude to process it** — e.g. "process the new statement export", in this repo. For a
   card export, Claude parses it, drops Payments & Refunds, and categorises every remaining
   transaction. For a Beem Report, incoming rows become deterministic Income/Beem Adjustment
   entries with no chat step needed, and outgoing rows are categorised from their message
   against the same fixed Sub-category list. Either way, Claude lists anything it's unsure about
   as Needs Review and waits for your input, then writes the deduped result to the live
   Transaction Log and archives the source file to `.data/processed/`. A card export and a Beem
   Report present together are each processed and archived on their own.

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
.env.example               Template for your .env (TRANSACTIONS_INBOX, SPREADSHEET_ID, etc.)
config/recurring-transactions.xlsx   Recurring items config (gitignored)
env/                       Service account key (gitignored)
.data/                     Sanitised exports awaiting processing; .data/processed/ once written
src/sanitising/            Sanitising script (run manually)
src/statement_export/      Statement Export parsing + pipeline wiring
src/beem/                  Beem Report parsing + deterministic Income categorisation
src/recurring/             Recurring Transactions Config expansion
src/transaction_log/       Dedupe + Google Sheets writer
tests/                     pytest suite
```

## Running tests

```
uv run pytest
```
