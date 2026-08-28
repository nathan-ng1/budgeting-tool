# Budgeting Tool

A personal, manually-triggered process that turns credit card statement exports into
categorised entries in a local budget database.

> **Already a collaborator on this private repo?** Skip straight to a guided install: download
> `setup.bat` (Windows) or `setup.command` (macOS) from the
> [latest Release](https://github.com/nathan-ng1/budgeting-tool/releases) and double-click it —
> see `docs/setup-guide.html` (Windows) or `docs/setup-guide-mac.html` (macOS) for the full
> walkthrough (ADR-0017, issue #117). The manual steps below stay here for advanced use,
> troubleshooting, and Linux setups (untested).

See `CONTEXT.md` for the full glossary of terms used below (Statement Export, Sanitising,
Transaction Log, Needs Review, Recurring Transaction, etc).

## How it works, in short

1. You download a **Statement Export** (a raw CSV) from your card issuer's online banking into
   a local Transactions Inbox.
2. A script **sanitises** it — strips personal identifiers — and moves it into `.data/`.
3. You run `windows/process_statement_export.bat` / `mac/process_statement_export.command` (or
   `uv run python -m statement_export`) to process it.
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

- **Windows or macOS** — the day-to-day flow uses a `windows/*.bat` script (Windows-style paths in
  `.env`) or a `mac/*.command` script (forward-slash paths), both wrapping the same underlying
  `uv run python -m ...` commands. Linux should work with the `mac/` scripts adapted, but that's
  untested.
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
- Optional: **[Node.js](https://nodejs.org/) 20+**, only needed to build the Dashboard's frontend
  (step 4 of "One-time setup"). The Statement Export pipeline doesn't need it.
- Optional (for this manual walkthrough): **[GitHub CLI (`gh`)](https://cli.github.com/)**, logged
  in — needed for Claude's issue-tracker agent skill (`docs/agents/issue-tracker.md`), and for
  `open_dashboard`'s best-effort "update available" notice and `update` (ADR-0019); both degrade
  to doing nothing if `gh` isn't set up. It's a *required*, guided step in `setup.bat`/
  `setup.command` (`docs/setup-guide.html`/`docs/setup-guide-mac.html`), since that path also
  needs it to clone this private repo.
- Optional: a **Google account** with access to Google Cloud Console and your own budget
  spreadsheet, only if you want the historical/reference Google Sheets MCP connection for ad hoc
  chat queries or a one-off export — see `docs/agents/google-sheets-mcp.md` for setup (install
  with `uv sync --extra mcp` instead of step 1's plain `uv sync`). Not needed to run the pipeline
  itself; the live Transaction Log is a local SQLite database (step 2 below).

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

The historical/reference Google Sheets MCP connection (`docs/agents/google-sheets-mcp.md`) needs its
own `SERVICE_ACCOUNT_PATH`, but that's set directly in its MCP server registration, not in `.env` —
nothing in the pipeline reads it from here.

Any of these also work as a real environment variable set in your shell for the session (e.g.
`$env:BEEM_USERNAME = "your_beem_username"` in PowerShell) — `.env` just saves you from setting
them every session.

### 3. Set up the recurring transactions config (optional)

If you have predictable recurring items (salary, rent, mortgage, subscriptions), add one rule per
item on the Dashboard's **Settings** tab (amount, type, category, notes, frequency/interval/day,
start/end date) — see "Editing the Recurring Transactions Config" below. That needs the frontend built
(step 4); if you'd rather not build it, you can insert rows into your database's `recurring_rules`
table directly via `sqlite3 <DATABASE_PATH>`.

### 4. Build the Dashboard frontend (optional)

Only needed if you want the Dashboard (below). It's a React app built with Vite, so it needs
[Node.js](https://nodejs.org/) 20+ alongside `uv`:

```
cd frontend
npm install
npm run build
```

That writes the built page into `src/dashboard/static/`, which the Dashboard's own server serves.
Both the built output and `node_modules/` are gitignored — rebuild after pulling frontend changes.

## Day-to-day usage

### Processing a new Statement Export

1. **Download** the export unchanged into the Transactions Inbox (a folder outside this repo —
   the sanitising step never lets Claude read it directly; see
   [ADR-0001](docs/adr/0001-sanitising-happens-outside-claudes-read-access.md)). Name it
   `{Issuer}_{yyyymmdd}.csv` (e.g. `ANZ_20260830.csv`) — the issuer prefix must match a handler
   registered in `src/sanitising/sanitise.py` (currently `ANZ`, `Beem`, and `NAB`).

2. **Run `windows/process_statement_export.bat`** (Windows) or
   **`mac/process_statement_export.command`** (macOS) — or the two steps either one wraps, below.
   This sanitises anything new in the Transactions Inbox, then categorises and writes it:

   ```
   uv run python -m sanitising
   uv run python -m statement_export
   ```

   Sanitising moves every recognised export from the inbox into `.data/`, stripping personal
   identifiers per-issuer. `statement_export` then handles each file sitting in `.data/` by
   issuer: for a card export, it parses it and categorises every transaction via your configured
   `CATEGORISER_BACKEND` — a positive-Amount row is classified as a genuine Refund (written as
   Income/Refund) or a Bill Payment (dropped, never written). For a Beem Report, incoming
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

### Viewing the Dashboard

Double-click **`windows/open_dashboard.bat`** (Windows) or **`mac/open_dashboard.command`**
(macOS — right-click → Open the first time, see `docs/setup-guide-mac.html`). It starts the local
server and opens the Dashboard in Chrome once the server is actually accepting connections
(falling back to your default browser if Chrome isn't installed). Leave the window it opens
running while you use the Dashboard - closing it stops the server. Running it again while the
Dashboard is already up just opens the page rather than starting a second server.

Or, equivalently, by hand:

```
uv run python -m dashboard
```

Then open <http://127.0.0.1:8765>. The Dashboard's Overview tab shows one month at a time: the
Income/Expenses/Net Balance/Transferred tiles, where your income went, spending by Category,
Budgeted vs Actual, your top 5 expenses, and expenses over the month. Pick a month with the
Jul–Jun pills — it opens on the current month of the current Financial Year. The **Transactions**
tab lists, adds, edits, and deletes individual transactions by hand, with search/sort/export. The
**Budget** tab edits each Category's per-month budget and shows the standing Budget Suggestion
write-up (see `generate_budget_suggestion` below). The **Settings** tab edits Category
Management (below) and your Recurring Transactions Config (below). See `docs/dashboard-guide.html`
for a full walkthrough of every tab and script.

It runs entirely on your machine and reads the local database directly; no transaction data
leaves the machine ([ADR-0008](docs/adr/0008-dashboard-is-a-local-web-app-not-a-hosted-artifact.md)),
and the page loads no fonts, scripts, or styles from the network. Set `DASHBOARD_PORT` in `.env`
to serve on a different port - `open_dashboard` reads it too. If the page tells you the
frontend hasn't been built, run step 4 of the one-time setup above.

### Editing the Recurring Transactions Config

The Dashboard's **Settings** tab lists every rule in your Recurring Transactions Config and lets
you add, edit, and delete them — no `sqlite3` needed. Each rule's Day follows its Start Date (a
Weekly rule starting on a Wednesday recurs on Wednesdays), so the two can't contradict each other;
a Monthly rule's Day stays editable so you can set Day 31 and have short months clamp to their
last day. Leave End Date blank for a rule that recurs indefinitely.

Edits take effect on the next `uv run python -m statement_export` run (or recurring-transactions
check) with no separate sync step — the Dashboard and the pipeline read the same database.
Categories offered in the form are the valid `(Type, Category)` pairs from
`src/transaction_log/categories.py`, and the store rejects any other pair.

To work on the frontend itself, `npm run dev` in `frontend/` starts Vite with hot reload on
<http://127.0.0.1:5173>, proxying `/api` through to `uv run python -m dashboard` on 8765 — so run
both together.

## Repo layout

```
CONTEXT.md                 Domain glossary
docs/adr/                  Architecture decisions
docs/agents/                Agent-facing runbooks (issue tracker, MCP, pipeline)
docs/setup-guide.html       Windows Installation Pack guide (self-contained, terracotta-themed)
docs/setup-guide-mac.html   macOS Installation Pack guide (same, for mac/*.command)
docs/dashboard-guide.html   Dashboard usage guide - the four tabs, and what each script does
.env.example               Template for your .env (TRANSACTIONS_INBOX, DATABASE_PATH, etc.)
.data/                     Sanitised exports awaiting processing; .data/processed/ once written
windows/                   Windows Installation Pack + day-to-day .bat scripts (see docs/setup-guide.html)
mac/                       macOS equivalents, one .command file per windows/*.bat (issue #117)
src/setup/                 .env-merging + update-availability logic every setup/update/
                            open_dashboard script (either OS) shells out to
src/sanitising/            Sanitising script (run manually)
src/statement_export/      Statement Export parsing, categorisation orchestration, entry point
src/beem/                  Beem Report parsing + deterministic Income categorisation
src/categorisation/        Pluggable Categoriser interface + Claude/Codex/OpenAI-compatible backends
src/recurring/             Recurring Transactions Config schedule expansion
src/database/              Local SQLite store (Transaction Log + Recurring Transactions Config)
src/transaction_log/       Dedupe logic + Candidate/ExistingRow types
src/dashboard/             Dashboard server + Month Overview query; serves the built frontend
frontend/                  Dashboard frontend (React + Vite), built into src/dashboard/static/
docs/mockups/              Approved Claude Design mockup the Overview tab is built to
tests/                     pytest suite
tests/dev/windows/         Frontend-dev-only .bat scripts (Vite hot reload), not day-to-day
tests/dev/mac/             Same, as .command scripts for macOS
```

## Running tests

```
uv run pytest
```

The Dashboard frontend has its own suite (Vitest + Testing Library):

```
cd frontend
npm test
```
