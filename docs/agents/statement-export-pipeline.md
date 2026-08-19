# Running the Statement Export pipeline

How to get a new credit card Statement Export from your bank's website into the Transaction
Log. See `CONTEXT.md` for the vocabulary used below (Statement Export, Sanitising, Needs
Review, Recurring Transaction, etc).

## When a new export arrives

1. **Download** the export from your card issuer's online banking, unchanged, into the
   Transactions Inbox (path set via `TRANSACTIONS_INBOX` in `.env`) — the sanitising step never
   lets Claude read this location directly (see
   [ADR-0001](../adr/0001-sanitising-happens-outside-claudes-read-access.md)). Name it
   `{Issuer}_{yyyymmdd}.csv` (e.g. `ANZ_20260830.csv`) — the issuer prefix must match a handler
   registered in `src/sanitising/sanitise.py` (currently `ANZ`, `Beem`, and `NAB`). A Beem
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

3. **Process it** — run this yourself, not via Claude:
   ```
   uv run python -m statement_export
   ```
   (Or just run `process_statement_export.bat`, which does steps 2 and 3 together.) The script
   looks at what's sitting in `.data\` and handles each file there by issuer:
   - **Card export (e.g. ANZ)**: parse the export (both signs — negative spend and positive
     Bill Payment/Refund rows all flow into categorisation, see
     [ADR-0007](../adr/0007-classify-refunds-vs-bill-payments-via-the-categorisation-backend.md))
     and assign a Type/Category to every transaction against the fixed mapping in
     `src/transaction_log/categories.py`, via whichever backend `CATEGORISER_BACKEND` selects. A
     positive-Amount row is classified by the backend as a genuine Refund (written as Type
     Income, Category Refund) or a Bill Payment (`is_bill_payment: true` — dropped before
     `Candidate`s are built, never written, never blocks archiving); an ambiguous one goes to
     Needs Review, where the terminal resolver can pick a Type/Category or drop it as a Bill
     Payment.
   - **Beem Report**: `beem.parser.parse()` keeps both directions (unlike a card export, a
     positive row here is real Income, not a Bill Payment/Refund judgement call).
     `beem.parser.categorise()` splits the parsed rows: incoming (positive) rows become
     deterministic `Type: Income, Category: Beem Adjustment` candidates with no model
     call needed; outgoing (negative) rows are categorised from their Message against the same
     fixed Expense Category list used for card Transactions.
   - Either way: anything the backend flags `needs_review` is prompted right there in the
     terminal (via `statement_export.terminal_review.TerminalReviewer`), and nothing is written
     until every Needs Review item for that file is resolved.
   - Once resolved, due Recurring Transactions (from the local database's `recurring_rules`
     table, capped at that file's own last transaction date) are expanded and merged with that
     file's candidates, and the combined, deduped list is written to the live Transaction Log via
     `transaction_log.writer.resolve_writes` / `statement_export.orchestrator.run` — the same
     generic write path regardless of source or backend.
   - That source file is archived from `.data\` to `.data\processed\` on a successful write. If
     a card export and a Beem Report are both present, each is categorised, written and archived
     as its own `statement_export.orchestrator.run` call — dedupe against the live log means
     running the script more than once in a session (e.g. after an aborted run) is always safe.
   - If a file's categorisation backend returns something that doesn't match the expected
     structured response (malformed JSON, wrong result count, an invalid Type/Category
     pair), that file's run **aborts**: nothing is written or archived for it, and the script
     moves on to any other outstanding file. Rerun once the underlying issue (backend config,
     model choice, etc.) is fixed.

No statement export needed? Recurring Transactions (salary, mortgage, subscriptions, etc.)
still get checked and written on their own — you can ask Claude to "check for due recurring
transactions" at any time without a new export present. This one check remains an interactive,
chat-driven use of `transaction_log.writer.resolve_writes` — there's no standalone script for it,
since (unlike categorisation) it was never the thing this feature scripted.

## What's deterministic vs. what needs a model's judgement

Per [ADR-0002](../adr/0002-recurring-schedule-expansion-happens-in-a-script.md) and
[ADR-0004](../adr/0004-categorisation-backend-is-pluggable-and-scripted.md), the mechanical parts
run as plain scripts so they're exactly right every time, and even the judgement-call part
(categorisation) runs through a script now, with the judgement itself delegated to a pluggable
model backend rather than improvised in chat:

- `src/sanitising/` — moves and sanitises exports (run manually, step 2 above).
- `src/statement_export/parser.py` — parses a Statement Export into raw Transactions, both signs
  (negative spend and positive Bill Payment/Refund rows all flow into categorisation).
- `src/beem/parser.py` — parses a Beem Report (keeping both directions) and splits it into
  deterministic Income candidates and outgoing rows still needing categorisation.
- `src/categorisation/` — the pluggable `Categoriser` interface and its three backends
  (`claude_backend.py`, `codex_backend.py`, `openai_compatible_backend.py`). This is where a
  model's judgement call happens (is this Square charge a donation or a coffee?) — a fixed rule
  set can't make that call reliably, so it's delegated to whichever backend `CATEGORISER_BACKEND`
  selects, not hand-coded.
- `src/statement_export/orchestrator.py` — drives categorise → Needs Review terminal prompt loop
  → Recurring Transaction merge → dedupe/write/archive, for a single source file. Aborts (no
  write, no archive) if the backend's response doesn't match the expected structured contract.
- `src/statement_export/run.py` + `src/statement_export/__main__.py` — the actual entry point
  (`uv run python -m statement_export`): discovers outstanding files in `.data\`, routes each to
  the orchestrator by issuer, and prints a summary.
- `src/database/store.py` — reads Recurring Transactions Config rows from the local database.
  `src/recurring/schedule.py` — expands them into due occurrences.
- `src/transaction_log/writer.py` + `src/database/store.py` — dedupe against the live log and
  write.

## Dry runs

Pass `--dry-run` to `uv run python -m statement_export` (or `process_statement_export.bat
--dry-run`) to preview a run before committing to it — you're still prompted through any Needs
Review items, so you see and answer them, but nothing is written to the local database and no
source file is archived. Useful when trying an unfamiliar or weaker local model backend for the
first time.

## Manual backend verification

Real subprocess/network calls to each backend are deliberately out of scope for the automated
test suite (every test injects a fake process runner or HTTP transport) — each backend needs a
one-off manual check against the real CLI/endpoint before you rely on it:

- **`claude`** (`CATEGORISER_BACKEND=claude`) — verified manually: a real `claude -p ... --output-format
  json --json-schema ...` call against two sample transactions returned a valid, correctly
  schema-shaped `structured_output` and categorised both transactions sensibly (a grocery store
  as Expenses/Groceries, a streaming service as Bills & Subscriptions/Subscriptions). Note this
  run predates the Type/Category rename (ADR-0006) — the two Categories it reports are under the
  retired names; the equivalents now are Expense/Groceries and Expense/Subscriptions.
- **`codex`** (`CATEGORISER_BACKEND=codex`) — **not yet manually verified.** `codex_backend.py`'s
  invocation (`codex exec <prompt>`, stdout parsed directly as the batch JSON) is based on Codex
  CLI's documented non-interactive behaviour, not a live run. Verify once against a real Codex
  CLI install and update this note with the result.
- **`openai-compatible`** (`CATEGORISER_BACKEND=openai-compatible`) — **request/response
  contract verified, but not viable against a small local model for a real statement.** A live
  call against local Ollama (`qwen3.5:9b`, 6.6GB q4, on an 8GB-VRAM RTX 3060 Ti) confirmed the
  request shape and JSON-schema contract work end-to-end: an isolated 3-transaction batch
  categorised correctly (including a sensible `needs_review` flag on an ambiguous merchant). But
  a full statement (125 transactions) failed with `Expected 125 results, got 18` — the model
  ran out of context mid-response and the schema-constrained decoder silently closed the JSON
  early rather than erroring. Ollama's VRAM-based default context is only 4096 tokens; raising it
  to 16384 via a custom Modelfile (`PARAMETER num_ctx 16384`) improved this to 50/125, and 32768
  was tried but not completed. Qwen3-family models generate hidden "thinking" tokens by default,
  which is the likely reason so few results fit even at 16k-32k context — this wasn't
  investigated further (e.g. disabling thinking mode, or batching transactions into smaller
  chunks). `parse_batch_response` correctly detected the short result count and aborted cleanly
  (nothing written, no corruption) both times, so the failure mode itself is safe — this backend
  just isn't practically usable for a full statement against this model/hardware combination
  without further work. `CATEGORISER_BACKEND` was reverted to `claude` for real use. Worth
  revisiting with either a larger/faster local model, thinking disabled, or batched requests.
