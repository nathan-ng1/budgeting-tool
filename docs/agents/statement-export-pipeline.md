# Running the Statement Export pipeline

How to get a new credit card Statement Export from your bank's website into the Transaction
Log. See `CONTEXT.md` for the vocabulary used below (Statement Export, Sanitising, Needs
Review, Recurring Transaction, etc).

## When a new export arrives

1. **Download** the export from your card issuer's online banking, unchanged, into the
   Transactions Inbox (`D:\natha\Documents\Transactions`) — Claude never reads this location
   directly (see [ADR-0001](../adr/0001-sanitising-happens-outside-claudes-read-access.md)).
   Name it `{Issuer}_{yyyymmdd}.csv` (e.g. `ANZ_20260830.csv`) — the issuer prefix must match
   a handler registered in `src/sanitising/sanitise.py` (currently just `ANZ`).

2. **Sanitise it** — run this yourself, not via Claude:
   ```
   uv run python -m sanitising
   ```
   This moves every recognised export from the inbox into `.data\`, stripping personal
   identifiers per-issuer (a no-op for ANZ). Anything sitting directly in `.data\` afterwards
   is outstanding and hasn't been processed into the Transaction Log yet.

3. **Ask Claude to process it** — e.g. "process the new statement export" in this repo. Claude
   will:
   - Parse the export and drop any Payments & Refunds (positive-Amount rows) before
     categorising anything.
   - Assign a Category/Sub-category to every remaining transaction against the fixed mapping
     in `CONTEXT.md`.
   - List anything it isn't confident about as **Needs Review**, inline in chat, and wait for
     you to assign those before writing anything.
   - Once every Needs Review item is resolved, expand any due Recurring Transactions (from
     `config\recurring-transactions.xlsx`, capped at the export's own last transaction date)
     and write the combined, deduped candidate list to the live Transaction Log.
   - Archive the source file from `.data\` to `.data\processed\` on a successful write.

No statement export needed? Recurring Transactions (salary, mortgage, subscriptions, etc.)
still get checked and written on their own — you can ask Claude to "check for due recurring
transactions" at any time without a new export present.

## What's deterministic vs. what needs Claude's judgement

Per [ADR-0002](../adr/0002-recurring-schedule-expansion-happens-in-a-script.md), the mechanical
parts run as plain scripts so they're exactly right every time:

- `src/sanitising/` — moves and sanitises exports (run manually, step 2 above).
- `src/statement_export/parser.py` — parses a Statement Export into raw Transactions, dropping
  Payments & Refunds.
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
