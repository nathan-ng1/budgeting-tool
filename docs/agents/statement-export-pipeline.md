# Running the Statement Export pipeline

How to get a new credit card Statement Export from your bank's website into the Transaction
Log. See `CONTEXT.md` for the vocabulary used below (Statement Export, Sanitising, Needs
Review, Recurring Transaction, etc).

## When a new export arrives

1. **Download** the export from your card issuer's online banking, unchanged, into the
   Transactions Inbox (`D:\natha\Documents\Transactions`) — Claude never reads this location
   directly (see [ADR-0001](../adr/0001-sanitising-happens-outside-claudes-read-access.md)).
   Name it `{Issuer}_{yyyymmdd}.csv` (e.g. `ANZ_20260830.csv`) — the issuer prefix must match
   a handler registered in `src/sanitising/sanitise.py` (currently `ANZ` and `Beem`). A Beem
   Report (see `CONTEXT.md`) follows the same naming convention (e.g. `Beem_20260830.csv`) and
   can sit in the Inbox alongside a card export — both are sanitised and processed in the same
   run.

2. **Sanitise it** — run this yourself, not via Claude:
   ```
   uv run python -m sanitising
   ```
   This moves every recognised export from the inbox into `.data\`, stripping personal
   identifiers per-issuer (a no-op for ANZ). Anything sitting directly in `.data\` afterwards
   is outstanding and hasn't been processed into the Transaction Log yet.

3. **Ask Claude to process it** — e.g. "process the new statement export" in this repo. Claude
   looks at what's sitting in `.data\` and handles each file there by issuer:
   - **Card export (e.g. ANZ)**: parse the export and drop any Payments & Refunds (positive-
     Amount rows) before categorising anything, then assign a Category/Sub-category to every
     remaining transaction against the fixed mapping in `CONTEXT.md`.
   - **Beem Report**: `beem.parser.parse()` keeps both directions (unlike a card export, a
     positive row here is real Income, not a droppable Payments & Refunds credit).
     `beem.parser.categorise()` splits the parsed rows: incoming (positive) rows become
     deterministic `Category: Income, Sub-category: Beem Adjustment` candidates with no chat
     step needed; outgoing (negative) rows are categorised from their Message against the same
     fixed Expense/Bills & Subscriptions Sub-category list used for card Transactions.
   - Either way: list anything it isn't confident about as **Needs Review**, inline in chat, and
     wait for you to assign those before writing anything.
   - Once every Needs Review item for a given source file is resolved, expand any due Recurring
     Transactions (from `config\recurring-transactions.xlsx`, capped at that file's own last
     transaction date), merge them with that file's candidates, and write the combined, deduped
     list to the live Transaction Log via `transaction_log.writer.resolve_writes` /
     `statement_export.pipeline.run` — the same generic write path regardless of source.
   - Archive that source file from `.data\` to `.data\processed\` on a successful write. If a
     card export and a Beem Report are both present, each is categorised, written and archived
     as its own `statement_export.pipeline.run` call — dedupe against the live log means running
     the pipeline more than once in a session is always safe.

No statement export needed? Recurring Transactions (salary, mortgage, subscriptions, etc.)
still get checked and written on their own — you can ask Claude to "check for due recurring
transactions" at any time without a new export present.

## What's deterministic vs. what needs Claude's judgement

Per [ADR-0002](../adr/0002-recurring-schedule-expansion-happens-in-a-script.md), the mechanical
parts run as plain scripts so they're exactly right every time:

- `src/sanitising/` — moves and sanitises exports (run manually, step 2 above).
- `src/statement_export/parser.py` — parses a Statement Export into raw Transactions, dropping
  Payments & Refunds.
- `src/beem/parser.py` — parses a Beem Report (keeping both directions) and splits it into
  deterministic Income candidates and outgoing rows still needing categorisation.
- `src/recurring/config.py` — expands the Recurring Transactions Config into due occurrences.
- `src/transaction_log/writer.py` + `src/transaction_log/sheets_client.py` — dedupe against the
  live log and write.
- `src/statement_export/pipeline.py` — wires the above together: given an already-categorised
  candidate list, resolve what's new, write it, archive the source file.

Categorising each transaction (assigning Category/Sub-category, and flagging Needs Review) is
the one step that isn't scripted — it needs judgement calls a fixed rule set can't make
reliably (is this Square charge a donation or a coffee?), so it's Claude's job each run, not
`src/statement_export/pipeline.py`'s.

## Live writes are real

Running this against a live `.data\` export writes real rows to your real budget spreadsheet
and archives the source file — there's no dry-run mode. If you want to preview what would be
written before committing to it, ask Claude to list the categorisation first without running
the pipeline.
