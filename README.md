# Budgeting Tool

A personal, manually-triggered process that turns credit card statement exports into
categorised entries in a local budget database.

See `CONTEXT.md` for the full glossary of terms used below (Statement Export, Sanitising,
Transaction Log, Needs Review, Recurring Transaction, etc).

## How it works, in short

1. You download a **Statement Export** (a raw CSV) from your card issuer's online banking into
   a local Transactions Inbox.
2. A script **sanitises** it — strips personal identifiers — and moves it into `.data/`.
3. You run `process_statement_export.bat` (or `uv run python -m statement_export`) to process it.
   The script parses the export, assigns a Type/Category to each transaction via
   whichever **categorisation backend** you've configured (Claude Code, Codex CLI, or an
   OpenAI-compatible endpoint like a local Ollama), prompts you in the terminal to resolve
   anything it isn't confident about (**Needs Review**), then writes the categorised transactions
   to the **Transaction Log** in your local SQLite database and archives the source file.
4. Recurring items (salary, rent, mortgage, subscriptions, etc.) are expanded from the database's
   Recurring Transactions Config and written the same way, with or without a new export present.

Pass `--dry-run` to preview a run — including your Needs Review answers — without writing to your
real database or archiving anything.

## Prerequisites

- **Windows** — the day-to-day flow uses a `.bat` script and Windows-style paths by convention.
  It should work on macOS/Linux with small tweaks (a shell script instead of `.bat`,
  forward-slash paths in your `.env`), but that's untested.
- **One of the following, to categorise transactions** (set via `CATEGORISER_BACKEND` in `.env`,
  step 3 below):
  - **[Claude Code](https://docs.claude.com/en/docs/claude-code)**, installed and logged in —
    categorisation shells out to its non-interactive `claude -p` mode, using whatever auth
    Claude Code is already configured with (subscription or pay-as-you-go API billing through the
    [Anthropic Console](https://console.anthropic.com/)). No separate API key needed just for
    this.
  - **[Codex CLI](https://developers.openai.com/codex/cli)**, installed and logged in —
    categorisation shells out to its non-interactive `codex exec` mode, using your existing Codex
    CLI auth. No separate OpenAI API key needed just for this.
  - Any **OpenAI-compatible HTTP endpoint** — a local [Ollama](https://ollama.com/) install, or a
    hosted provider like OpenAI itself, OpenRouter, or LM Studio. Configured with a base URL, API
    key, and model name.
- **[`uv`](https://docs.astral.sh/uv/)** and **Python 3.12+**.
- **Git**, to clone this repo.
- Optional: **[GitHub CLI (`gh`)](https://cli.github.com/)**, only needed if you also want
  Claude's issue-tracker agent skill (`docs/agents/issue-tracker.md`) to file/read GitHub issues
  against your own fork/clone.
- Optional: a **Google account** with access to Google Cloud Console and your own budget
  spreadsheet, only if you want the historical/reference Google Sheets MCP connection for ad hoc
  chat queries or a one-off export — see `docs/agents/google-sheets-mcp.md`. Not needed to run the
  pipeline itself; the live Transaction Log is a local SQLite database (step 3 below).

## Setting this up for someone else

Nothing personal is hardcoded in source — every per-person setting (`TRANSACTIONS_INBOX`,
`DATABASE_PATH`, `BEEM_USERNAME`, `CATEGORISER_BACKEND` and its backend-specific settings) lives
in a gitignored `.env`, copied from `.env.example` (step 2 below). To hand this repo to someone
else, they clone the repo and copy their own `.env` from `.env.example` — nothing from your
`.env` or your local database file should be shared, since those hold real financial figures. They
then run through "One-time setup" below as-is, using their own paths.

## One-time setup

### 1. Clone the repo and install dependencies

This project uses [`uv`](https://docs.astral.sh/uv/) and Python 3.12+.

```
git clone <this-repo-url>
cd budgeting-tool
uv sync
```

### 2. Configure your `.env` file

Every per-person setting — none of them are hardcoded in source — is read from environment
variables, loaded from a `.env` file in the repo root (gitignored, so it never gets committed).
Copy the template and fill it in:

```
cp .env.example .env
```

| Variable | Required | Meaning |
|---|---|---|
| `TRANSACTIONS_INBOX` | yes | Absolute path to the folder outside this repo where you download raw Statement Exports. Read by `uv run python -m sanitising`. |
| `DATABASE_PATH` | yes | Path to your local SQLite database file — the live Transaction Log and Recurring Transactions Config. Created automatically on first run if it doesn't exist yet. |
| `BEEM_USERNAME` | only for Beem reports | Which side of each row (`Payer`/`Recipient`) is you, so the Beem sanitising handler can derive a signed amount. |
| `CATEGORISER_BACKEND` | yes | Which categorisation backend to use: `claude`, `codex`, or `openai-compatible`. Read by `uv run python -m statement_export`. |
| `OPENAI_COMPATIBLE_BASE_URL` | only for the `openai-compatible` backend | Base URL of the OpenAI-compatible chat-completions endpoint (e.g. `http://localhost:11434/v1` for a local Ollama). |
| `OPENAI_COMPATIBLE_API_KEY` | only if your endpoint requires one | API key sent as a Bearer token. Most local Ollama installs don't need a real one. |
| `OPENAI_COMPATIBLE_MODEL` | only for the `openai-compatible` backend | Model name to request (e.g. `llama3`). |
| `SERVICE_ACCOUNT_PATH` / `SPREADSHEET_ID` | no | Only needed for the historical/reference Google Sheets MCP connection — see `docs/agents/google-sheets-mcp.md`. Not required to run the pipeline. |

Any of these also work as a real environment variable set in your shell for the session (e.g.
`$env:BEEM_USERNAME = "your_beem_username"` in PowerShell) — `.env` just saves you from setting
them every session.

### 3. Set up the recurring transactions config (optional)

If you have predictable recurring items (salary, rent, mortgage, subscriptions), insert one row
per rule into your database's `recurring_rules` table (amount, type, category, notes,
frequency/interval/day, start/end date) — e.g. via `sqlite3 <DATABASE_PATH>`. There's no editing
UI for this yet (see ADR-0008 for the planned Dashboard).

## Day-to-day usage

### Processing a new Statement Export

1. **Download** the export unchanged into the Transactions Inbox (a folder outside this repo —
   the sanitising step never lets Claude read it directly; see
   [ADR-0001](docs/adr/0001-sanitising-happens-outside-claudes-read-access.md)). Name it
   `{Issuer}_{yyyymmdd}.csv` (e.g. `ANZ_20260830.csv`) — the issuer prefix must match a handler
   registered in `src/sanitising/sanitise.py` (currently `ANZ`, `Beem`, and `NAB`).

2. **Run `process_statement_export.bat`** (or the two steps it wraps, below, if you're not on
   Windows). This sanitises anything new in the Transactions Inbox, then categorises and writes
   it:

   ```
   uv run python -m sanitising
   uv run python -m statement_export
   ```

   Sanitising moves every recognised export from the inbox into `.data/`, stripping personal
   identifiers per-issuer. `statement_export` then handles each file sitting in `.data/` by
   issuer: for a card export, it parses it, drops Payments & Refunds, and categorises every
   remaining transaction via your configured `CATEGORISER_BACKEND`. For a Beem Report, incoming
   rows become deterministic Income/Beem Adjustment entries with no model call needed, and
   outgoing rows are categorised from their message against the same fixed Category list.
   Either way, anything the backend isn't confident about is prompted as Needs Review right in
   the terminal, then the deduped result is written to the live Transaction Log and the source
   file is archived to `.data/processed/`. A card export and a Beem Report present together are
   each processed and archived on their own — dedupe against the live log means rerunning is
   always safe, including after an aborted run.

   Want a preview before anything is written? Pass `--dry-run`:
   `uv run python -m statement_export --dry-run` — it still prompts you through any Needs Review
   items so you can sanity-check the answers, but skips the write and the archive step.

### Checking recurring transactions

Recurring Transactions get expanded and written alongside any Statement Export processed above.
To check for due ones on their own (no new export), ask Claude Code to "check for due recurring
transactions" — this specific check is still an interactive, chat-driven use of
`transaction_log.writer.resolve_writes` rather than a scripted entry point.

Full walkthrough: `docs/agents/statement-export-pipeline.md`.

## Repo layout

```
CONTEXT.md                 Domain glossary
docs/adr/                  Architecture decisions
docs/agents/                Agent-facing runbooks (issue tracker, MCP, pipeline)
.env.example               Template for your .env (TRANSACTIONS_INBOX, DATABASE_PATH, etc.)
.data/                     Sanitised exports awaiting processing; .data/processed/ once written
src/sanitising/            Sanitising script (run manually)
src/statement_export/      Statement Export parsing, categorisation orchestration, entry point
src/beem/                  Beem Report parsing + deterministic Income categorisation
src/categorisation/        Pluggable Categoriser interface + Claude/Codex/OpenAI-compatible backends
src/recurring/             Recurring Transactions Config schedule expansion
src/database/              Local SQLite store (Transaction Log + Recurring Transactions Config)
src/transaction_log/       Dedupe logic + Candidate/ExistingRow types
tests/                     pytest suite
```

## Running tests

```
uv run pytest
```
