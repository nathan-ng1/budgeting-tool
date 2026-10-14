# Goals feature: what a locked "Goals" Category and a `goal_id` link would touch (research)

Retrieved 2026-10-14 from this repo only (source at commit `7b6c8a8`, `GLOSSARY.md`, `docs/adr/`, tests). Answers issue #208, a child of map #207. Pointers are `path:line`. This is an audit: no application code was changed and nothing here designs beyond the ticket. Anything not read directly from the repo is labelled **unverified**.

The design under audit is the map's "Settled while charting": a Goal table, a locked Savings-Type Category "Goals" predefined for every install, and a nullable `goal_id` on Transactions.

## Summary

1. **`locked` does less than its name suggests.** It blocks rename/delete (`src/database/store.py:372`, `:390`), the categorisation prompt and its response check (`src/transaction_log/categories.py:139`, `src/categorisation/prompt.py:143`), History Match learning (`src/categorisation/history.py:104-112`) and the Import template/commit (`src/dashboard/transactions.py:83`, `:259`, `:332`). It does **not** hide a Category from the Transactions form, the Recurring form or the Budget editor, and the store's `_require_valid_pair` (`src/database/store.py:409-418`) never checks it. Today a hand-added `Beem Adjustment` row is accepted. So "Goals can't go on a Recurring rule" needs new code in the frontend and the store; `locked` alone will not do it.
2. **Backend/History Match exclusion is already free.** Goals sits under the Savings Type, which is in `AI_EXCLUDED_TYPES` (`src/transaction_log/categories.py:74`), and it would also be `locked`. Both layers exclude it.
3. **The new table is cheap, the new column is not.** `SCHEMA` uses `CREATE TABLE IF NOT EXISTS` and runs on every open (`src/database/store.py:638`), so a `goals` table appears on existing installs unaided. A `goal_id` column on the existing `transactions` table does not: it needs an `ALTER TABLE` migration appended to `src/migration/registry.py`. The Goals Category row needs its own seeding migration, because `_seed_default_categories` never reseeds a non-empty table (`src/database/store.py:578-580`).
4. **No startup guard for pending migrations.** The Dashboard opens the Database with a bare `connect()` (`src/dashboard/__main__.py:16`). Only `update.bat`/`update.command` run migrations. Once `read_transactions` selects `goal_id`, an install that pulled the code but skipped the update would fail on every Transactions read.
5. **Foreign keys are not enforced** (no `PRAGMA foreign_keys` anywhere; `src/database/store.py:403-404` says so). `goal_id REFERENCES goals(id)` is documentation; "the Goal exists" and "Category is Goals" must be checked in code.
6. **Dedupe hazard is real but narrow.** The key is `(date, round(abs(amount), 2), notes)` (`src/transaction_log/writer.py:46-50`). Manual and split-tool inserts that go through `create_transaction`-style direct INSERTs are never deduped. Only Statement Export, "Run now" and Import go through `resolve_writes`. The sharp case is re-pointing a Recurring-generated Savings row at a Goal and changing its Notes: the Recurring rule re-expands its full history each run and would re-create the original row.
7. **Reset and Backup need little.** Backup is SQLite's online backup of the whole file (`src/database/backup.py:1-3`, `:11-13`), so new tables ride along. Reset rebuilds from `SCHEMA` plus the seed. Only the "what will be lost" counts (`src/database/store.py:490-507`, `frontend/src/components/DeleteData.jsx:99-103`) need a Goals line.
8. **ADR/glossary conflicts exist** (section 11): the Savings glossary entry says Savings is entered "via the Dashboard's Transactions tab or Recurring Transactions Config" and lists two predefined Categories; ADR-0022 says Savings Categories "must stay freely editable"; the Transaction Log entry lists five columns; ADR-0010/0021 tie the Transactions tab to the Financial Year, but a Goal's saved amount is date-independent.
9. **Release docs land at release time, not with the feature.** `CHANGELOG.md` has no Unreleased section (ADR-0029); the entry is written on the `chore/release-X.Y.Z` branch. `docs/dashboard-guide.html` says "four tabs" (`:143`) and has one card per tab (`:176-224`).

---

## 1. Transactions tab add/edit form and table

**Where the pieces are** (`frontend/src/components/Transactions.jsx` unless noted):

- Categories are fetched flat from `/api/categories` and grouped with `groupByType` (`:98-106`; `frontend/src/lib/categories.js:18-33`). `groupByType` takes every Category with no `locked` test, so a locked Category is offered. The only `locked` reads in the whole frontend (non-test) are `CategoryManagement.jsx:157` and `:175`.
- The Add form is `TransactionForm` (`:534-626`). Type select `:577-596`, Category select `:598-608`, Notes `:610-613`. There is precedent for a conditional extra under a field: the Bills & Subscriptions hint (`BILLS_HINT` `:531`, shown when `values.type === BILLS_AND_SUBSCRIPTIONS` `:542`, rendered `:591-595`).
- The in-row editor is `EditableRow` (`:791-848`): Category cell `:820-829`. Both forms share `useTransactionEditor` (`:495-526`), so a Goal picker added there reaches both.
- The read-only row renders `categoryLabel(transaction.category, emoji)` at `:412`. A Goal chip would sit in this cell (or the Notes cell `:413`).
- Form state lives in `frontend/src/lib/transactionForm.js`: `blankValues` `:5`, `valuesFrom` `:15`, `withType` `:25` (resets Category when Type changes, so it is also where a stale Goal would need clearing), `toPayload` `:36` (five fields only).
- API wrappers: `frontend/src/lib/transactionsApi.js:47-53` (`createTransaction`, `updateTransaction`).
- Table filter options come from the loaded rows' categories (`frontend/src/lib/transactionsView.js:23-25`), so "Goals" appears in the Category filter automatically once a row exists.

**Backend wire shape** (`src/dashboard/transactions.py`): `FIELDS` (`:23`) is the five required body fields; `as_payload` (`:46-54`) and `from_payload` (`:149-170`) carry five fields; `server._write_transaction` (`src/dashboard/server.py:380-399`) maps `ValueError` to 400 and `TransactionNotFound` to 404. A nullable `goal_id` (and a goal title for the chip) has to be added to `as_payload`, to `from_payload`, and to the `Transaction`/`Candidate` dataclasses (`src/transaction_log/entries.py:6`, `:42`).

**Persistence** (`src/database/store.py`): `read_transactions` JOINs categories (`:164-179`), `create_transaction` (`:181-193`) and `update_transaction` (`:195-207`) hard-code the five columns, and `update_transaction` is a full-row replace. Without an explicit rule, a PUT that omits `goal_id` would leave an old `goal_id` in place when the Category is changed away from Goals. `Transaction` is a frozen dataclass built by keyword in `store.py:170`, `:532` and in `tests/conftest.py:296-309`, so a trailing `goal_id: int | None = None` keeps existing constructions valid.

**Things to know:**

- The Transactions tab only loads one Financial/Calendar Year (`src/dashboard/queries.py:425-434`, ADR-0010). A Goal's saved amount "date doesn't matter" (map), so it cannot be derived from this endpoint's rows. `store.read_transactions()` returns everything (`store.py:164`), so a Goals query can sum all-time, but it is a separate read.
- CSV Export writes five columns and no goal (`transactions.py:24`, `:57-67`). A Goals row exports fine but cannot be re-imported (locked, section 7). Whether the export should carry the Goal title is a design call.
- `server.py:227` routes `POST /api/transactions` to `create_transaction`; `do_PUT` is at `:239`. A split tool that writes several rows atomically has no existing method: `append_rows` (`store.py:151-162`) does one `executemany` plus one commit but takes `Candidate`s with no goal field; `create_transaction` commits per call.
- Cents allocation: the only existing splitter is `recurring.split_from_payload` (`src/dashboard/recurring.py:65-86`), using `Decimal` and `ROUND_HALF_UP` and explicitly accepting drift. The split tool's "rows sum exactly to the total" rule is stricter, so that helper is a pattern, not a reuse.

## 2. Category Management (rename/delete rules for a locked, predefined Category)

- Rename: `LocalStore.update_category` raises `CategoryLocked` if `existing.locked` (`src/database/store.py:364-384`, check at `:372`). Delete: `delete_category` checks locked first (`:390`) and then in-use (`:393-400`). Both run before the in-use test, so a locked Category with Transactions gives the locked error, not the in-use one.
- The server maps `CategoryLocked` (a `ValueError`) to 400 (`src/dashboard/server.py:543-561`, comment at `:556-558`).
- The UI hides edit/delete and shows a lock: `frontend/src/components/CategoryManagement.jsx:157-179`.
- A locked Category cannot have even its emoji changed, since the whole update is refused (`store.py:372`). Seeding inserts no emoji (`:582-589`), so Goals would show with none unless the seed is extended.
- **Seeding hard-codes the locked name**: `1 if name == "Beem Adjustment" else 0` (`store.py:585`). `tests/conftest.py:26` repeats it for `FakeStore`. Adding Goals as a second locked name needs both changed (or generalised) or Goals seeds unlocked on new installs.
- `create_category` rejects a duplicate by exact, case-sensitive match (`store.py:354`, and `name TEXT NOT NULL UNIQUE` at `:30` is BINARY collation). A user could today create a Category named "Goals" under any Type, which matters for the migration (section 8).
- Two lists describe "predefined": `CATEGORIES_BY_TYPE` (`src/transaction_log/categories.py:30-60`) drives the seed, FakeStore and `count_data`'s "custom Categories" count (`store.py:499-505`). Adding Goals to `CATEGORIES_BY_TYPE["Savings"]` makes it predefined everywhere at once; `tests/transaction_log/test_categories.py:29` pins `{"Savings", "Investments"}` and will fail.
- Doc strings that say "Beem Adjustment today" and would need a touch: `categories.py:8`, `:145`; `store.py:101`; `history.py:106`.

## 3. Budget tab (Category Budgets on Savings Categories)

Goals appears with no code change, and so does every other locked Category.

- `BUDGETABLE_TYPES = TYPE_ORDER` (`src/dashboard/queries.py:23`; ADR-0023 consequence), so Savings is budgetable.
- `_budgetable_type_category_pairs` (`queries.py:315-328`) walks `categories_by_type`, which explicitly includes locked Categories (`categories.py:116-127` docstring). `get_budget_editor` (`:331`) and the Full year grid use it. `Beem Adjustment` already shows in the Budget editor on this basis.
- `store.upsert_category_budget` validates only the pair (`store.py:312-322`, `:315`), so a Goals budget can be set.
- Actuals: `_budgeted_vs_actual_rows` (`queries.py:635-668`) includes any Category with a budget or non-zero actual. A Goals row shows under Savings in Overview's Budgeted vs Actual, and reads favourable when above budget (`frontend/src/components/BudgetedVsActual.jsx:30-41`).
- Left to Budget counts Savings Categories (`frontend/src/lib/budgetTotals.js:48`), so a Goals budget reduces it like Savings/Investments.
- Budget Suggestion drops Income and Savings rows before the Advisor sees them (`src/budget_suggestions/run.py:35`), so Goals never reaches it.
- Open point: whether a Category Budget on "Goals" is wanted at all; the design says "unchanged", which is what happens by default.

## 4. History Match and the categorisation backends (can Goals ever be assigned or matched?)

Confirmed: no, by two independent layers.

- **Type exclusion**: `types_with_categories` drops `AI_EXCLUDED_TYPES = {"Savings"}` (`categories.py:74`, `:104-113`). Goals is a Savings Category, so the prompt never lists it (`src/categorisation/prompt.py:52-53`).
- **Locked exclusion**: `assignable_categories_by_type` skips locked Categories (`categories.py:139-158`). The response check rejects anything not assignable (`prompt.py:143`), so a model that invents "Savings / Goals" gets `MalformedResponseError`.
- **History Match**: `split_history_matches` (`src/categorisation/history.py:42-74`) only matches a pair in `_assignable_pairs` (`:99-101`), which comes from the same assignable view, so never a Savings pair.
- **Learning**: `_learnable` (`:104-112`) drops rows in locked Categories. Goals rows (Notes defaulting to a Goal title) therefore never become prompt examples and never use up one of the 200 example slots. Savings/Investments rows are not locked and still count toward those slots today.
- **Needs Review**: `TerminalReviewer()` is built with its default argument, the hard-coded `CATEGORIES_BY_TYPE` dict (`src/statement_export/__main__.py:29`, `src/statement_export/terminal_review.py:20`). It offers `types_with_categories(...)`, which excludes Savings, so Goals is unreachable. (Pre-existing gap, not Goals-specific: that dict includes `Beem Adjustment` under Expense and ignores user-created Categories.)
- **Orchestrator**: its pair check uses the live table without a locked/Savings filter (`src/statement_export/orchestrator.py:97`), but it only sees pairs that survived the layers above or came from Needs Review.
- **Beem path**: the Beem parser writes incoming rows deterministically as Expense / Beem Adjustment (ADR-0015) and sends outgoing rows to the backend; neither can produce Savings.
- No `goal_id` can arise from this pipeline: `Candidate` has no such field, and `append_rows` (`store.py:155-161`) would leave the new column NULL.

## 5. Recurring Transactions Config Category dropdown (is Goals excluded?)

**No. It would appear, and nothing server-side stops it.**

- The Recurring form groups the same flat list with `groupByType` (`frontend/src/components/RecurringRules.jsx:74`, `:284`; `frontend/src/lib/ruleForm.js:69`), with no `locked` filter. Goals would be offered under Savings.
- `create_recurring_rule` / `update_recurring_rule` validate the pair only (`store.py:248-258`, `:260-277`; both call `_require_valid_pair`). `src/dashboard/recurring.py:16-26` has no locked concept.
- A rule in Goals would expand into contributions with no `goal_id` (the expansion path builds `Candidate`s, `src/transaction_log/writer.py:35-43`). The map puts recurring contributions out of scope, so exclusion needs adding in two places: the dropdown, and a server check in the store (or a `locked`/manual-only test in `_require_valid_pair`). A frontend-only filter would repeat the Beem Adjustment gap. `Beem Adjustment` is currently selectable in the Recurring form too; no test pins that either way (searched `frontend/src/**/*.test.*` and `tests/`).
- The Transactions form needs the opposite: Goals selectable. So "exclude from Recurring" cannot just reuse a generic `locked` filter in `groupByType` without also removing it from Transactions.

## 6. Dedupe (Date + Amount + Notes): collision risk from split-tool rows

**Mechanics.** `resolve_writes` builds `existing_keys` from every stored row (`src/transaction_log/writer.py:20`) and skips a candidate whose key is present (`:24-27`). The key is `(date, round(abs(amount), 2), notes)` (`:46-50`). Two identical candidates inside one batch are **not** deduped against each other, only against stored rows. It is used by `pipeline.run` (Statement Export and "Run now", `src/statement_export/pipeline.py:28-33`), Import preview (`src/dashboard/transactions.py:271`) and Import commit (`:228-236`). `create_transaction` (the Transactions tab Add) and `update_transaction` do **not** dedupe.

**Risks for Goals rows:**

1. **Split-tool batch via `resolve_writes`.** Two contributions to the same Goal on the same day for the same amount collapse into one if they are written through that path and a matching row already exists. The split tool should not route through `resolve_writes`, or the dedupe must be a conscious choice. Goal titles are unique (map), so two different Goals never share Notes; but Notes are editable, so identical Notes across two Goals are possible.
2. **Remainder row.** The remainder goes to Savings/Investments with unspecified Notes. If it equals a Goal row's `(date, amount, notes)` they would collide on a later re-run through any dedupe path. Distinct Notes avoid it.
3. **Re-pointing a Recurring-generated row.** Recurring expansion re-checks its entire history every run (GLOSSARY "Recurring Transaction"; `pipeline.py:25-33`). The row stays deduped only while `(date, amount, notes)` is unchanged. Re-pointing a Savings row at a Goal and changing its Notes (the design defaults Notes to the Goal title) makes the next "Run now" or Statement Export insert the original Savings row again. The same behaviour exists today for any Notes edit on a recurring-generated row; the Goals design makes it more likely.
4. **Card-export collision.** A card Statement Export row with the same date, amount and Notes as a Goals row would be skipped as a duplicate. Practically negligible (Goals Notes are Goal titles), but it is the one cross-source path.
5. **Goal rename** does not change stored Notes (Notes is plain text), so existing keys are stable.

## 7. Backup / Reset (`DeleteData`) / Database move: what must include Goals tables

**Backup.** `database.backup.backup_to` uses SQLite's backup API on the live connection (`src/database/backup.py:1-3`, `:11-13`); `dashboard.database_info.make_backup` (`src/dashboard/database_info.py:19-29`) calls it. It copies the whole file, so `goals` and `goal_id` come along. Nothing to add. A downloaded Backup of a Goals-aware Database is a "complete Database in its own right" (GLOSSARY "Backup").

**Reset.** `database_reset.reset` (`src/dashboard/database_reset.py:65-107`) deletes the file and its `*.pre-migration-*.db` copies, then builds a fresh Database with `connect()` (`:65`); that applies `SCHEMA` and `_seed_default_categories`. A `goals` table in `SCHEMA` and Goals in the seed are therefore created automatically.
- The "what will be lost" list: `LocalStore.count_data` (`store.py:490-507`) returns row counts for `transactions`, `recurring_rules`, `category_budgets`, custom Categories and display settings. Goals (the Goal records themselves) are user data not covered by any of those. A `goals` count belongs there, and a `<li>` next to `frontend/src/components/DeleteData.jsx:99-103`. `summary_payload` (`database_reset.py:53-57`) spreads `count_data()`, so the payload needs no change. Tests: `tests/dashboard/test_database_reset_api.py`, `tests/database/test_store.py`.
- Contributions are ordinary Transactions and are already counted.
- If Goals is added to `CATEGORIES_BY_TYPE`, `count_data`'s "custom Categories" excludes it automatically (`store.py:499`).

**Database move / switch.** `check_foreign_database` (`src/dashboard/database_move.py:78-103`) opens the foreign file read-only and compares `schema_migrations` against `MIGRATIONS`: an older file is migrated first (`_migrate`, `:221-239`, which runs on a plain connection before `open_connection`), a file recording an unknown migration is refused ("made by a newer version"). A Goals migration added to the registry is therefore handled for moves and Backup restores with no extra code. Constraint from `_migrate`: a migration cannot assume `open_connection` has already run `SCHEMA`, so a Goals migration must create the `goals` table itself or run `SCHEMA` (as `categories_table.migrate` does at `src/migration/categories_table.py:22`).
- `_move` copies the Database file and pre-migration copies as files (`:255-294`); nothing table-specific.

## 8. Migration mechanism (ADR-0025): what a new table, a new column and a seeded Category need

**Mechanism.** `MIGRATIONS` in `src/migration/registry.py:15-19` is an append-only list of `Migration(name, migrate)`. Each runs once per Database, tracked in `schema_migrations` (`src/migration/runner.py:16-21`, `:52-70`). `python -m migration` (`src/migration/__main__.py:23-55`) backs the file up to `<name>.pre-migration-<stamp>.db` first. A brand-new Database (no `transactions` table) marks every registered migration as applied without running it (`src/database/store.py:624-637`), so migrations only ever run against pre-existing installs. `update.bat:107` and `update.command:104` are the only automatic callers.

| Change | New install | Existing install |
| --- | --- | --- |
| `goals` table | Add to `SCHEMA` (`store.py:26-77`); built by `executescript(SCHEMA)` at `:638`. | `CREATE TABLE IF NOT EXISTS` runs on next open (`:638`), so it appears without a migration. A migration that touches it **before** `open_connection` (database move, `database_move.py:226-232`) must create it itself. |
| `transactions.goal_id` | Put in the `transactions` `CREATE TABLE` in `SCHEMA` (`:35-42`). | **Needs a migration.** `CREATE TABLE IF NOT EXISTS` never alters an existing table. Use `ALTER TABLE ... ADD COLUMN goal_id INTEGER` (SQLite permits a NULL-default column with `REFERENCES`), guarded by a `PRAGMA table_info` check for idempotence, as `categories_table._migrate_table` does at `:73-75`. |
| Goals Category row | Add to `CATEGORIES_BY_TYPE["Savings"]` and make the seed lock it (`store.py:585`). | **Needs a migration**: `_seed_default_categories` returns early on a non-empty table (`:578-580`). `add_bills_and_subscriptions` is the template (`src/migration/add_bills_and_subscriptions.py:26-35`) but its guard is "Type has no Categories", which is wrong here (Savings has two); the guard would have to be by name. |

**Hazards to design around:**

- **Index on `goal_id` in `SCHEMA`.** `SCHEMA` runs against old files both at `open_connection` (`store.py:638`) and inside `categories_table.migrate` (`:22`). A `CREATE INDEX ... ON transactions(goal_id)` there would raise on an install whose column does not exist yet. Create any index inside the Goals migration.
- **Ordering with `categories_table`.** `_migrate_table` rebuilds `transactions` from explicit column lists (`categories_table.py:25-34`). Appending the Goals migration last (ordering is by registry) means it runs against the rebuilt table; the pre-#90 chain test (`tests/migration/test_registry.py`, "pre_categories_table") should be extended. Any later migration that rebuilds `transactions` must copy `goal_id`.
- **Name collision on seeding.** Names are unique across Types (`store.py:30`). If the live Database already holds a user-created Category called "Goals" (any Type, or "goals"), `INSERT OR IGNORE` would silently skip and leave no locked Category; the migration needs a defined behaviour (adopt and lock it if it is a Savings Category, otherwise fail loudly or rename). **Unverified against live data**: this audit did not read the live Database (its path is in `.env`, outside Claude's access, ADR-0001). Suggested check for whoever owns the data: `SELECT id, type, name, locked FROM categories WHERE lower(name) LIKE '%goal%'` and the row count for that `category_id` in `transactions` and `recurring_rules`.
- **No startup guard.** `dashboard/__main__.py:16` calls `connect()` and serves; nothing checks `pending(...)`. A code pull without `update` leaves `goal_id` missing and every `read_transactions` JOIN that selects it fails. The same hazard existed for the `categories_table` migration; `database_move` is the only place the Dashboard itself runs migrations.
- **Registry test pins the list**: `tests/migration/test_registry.py:10-14` asserts the exact three names. A new migration breaks it by design.
- **Case-insensitive uniqueness** of Goal titles is the map's rule. SQLite's `COLLATE NOCASE` folds ASCII only (SQLite documentation; **unverified here, not in the repo**), and Category names already use plain case-sensitive uniqueness (`store.py:30`, `:354`). Trim and case-fold in code if non-ASCII titles matter.
- **Dates**: stored as ISO text (`store.py:37`, `:53`); Goals start/end dates would follow the same convention.

## 9. Retail Edition: Dashboard-side parity

There is no Retail code in the repo yet; the only source is `docs/retail-edition-design-notes.md` (Paused, not an ADR). Relevant to Goals:

- Q3 and Q11: the Retail Edition is Dashboard-only and "excludes categorisation, sanitising, advisor and budget-suggestion code". Everything Goals adds (`goals`, `goal_id`, the Category, the tab, the endpoints) lives in `database/`, `migration/`, `transaction_log/`, `dashboard/` and `frontend/`, all of which Retail includes, so parity is by construction as long as Goals adds no import from the excluded packages. Existing coupling to be aware of: `src/dashboard/queries.py:14` imports `categorisation.history.normalise_notes`, which `history.py:15` ties to `statement_export.parser`. Not Goals-related; it matters for the Retail build and Goals code should not add to it.
- Q14: first launch seeds predefined Categories (ADR-0022). Goals arrives with the seed on a fresh Retail Database.
- Q17 (open): Retail "runs pending migrations on launch, with an automatic database backup first". The Goals migrations must be registry entries so that runner picks them up; also removes the "no startup guard" hazard from section 8 for Retail.
- Q13: Retail already needs "backup/restore"; the existing Backup copies all tables (section 7).
- The categorisation-side Goals exclusions (section 4) live in modules Retail drops, so nothing there needs parity.
- Q7/ADR-0030: the Database-location mechanism is Collaborator-only (ADR-0030 "Consequences"); not affected.
- The Version History source is edition-specific (ADR-0029, Retail notes "Version and Version History"); a Goals changelog line is a Collaborator `CHANGELOG.md` concern only. The Retail history is undecided.

## 10. Version History / changelog and `docs/dashboard-guide.html`

**Changelog.** `CHANGELOG.md` is hand-written, newest first, headings `## vX.Y.Z — YYYY-MM-DD` followed by flat bullets (`src/dashboard/changelog.py:15` `HEADING`; ADR-0029). There is **no Unreleased section**, and a test requires the newest entry's version to equal the installed package version (`docs/agents/releasing.md` step 1; `tests/dashboard/test_version_api.py`). Current version is `0.4.1` (`pyproject.toml:3`). So the Goals entry is written at release time on `chore/release-X.Y.Z`, not in the feature PR. Parse failure degrades to "isn't available" (`changelog.py:25-47`), so a malformed entry hides the whole history.

**Dashboard guide** (`docs/dashboard-guide.html`):
- `:143` "A tour of the Dashboard's four tabs" and `README.md:278` "the four tabs": both go stale with a fifth tab.
- `:163-174` "How to use?" is a four-step list; Goals has no step.
- `:176-224` "The Dashboard Tabs": one `.card` per tab (`:180` Overview, `:198` Transactions, `:206` Budget, `:215` Settings). A Goals card is needed, the Overview card (`:180-196`) needs the Goals tile, the Transactions card (`:198-204`) needs the Goal picker/chip, and the Settings card (`:215-223`) says a locked Category "can't be renamed or deleted", which Goals now joins.
- `frontend/src/App.test.jsx:1934` loops over the four tab names and needs the fifth.

## 11. Existing ADRs/glossary entries this design contradicts or extends

**Contradicts (text would become wrong):**

| Where | Says | Conflict |
| --- | --- | --- |
| `GLOSSARY.md` **Savings** (`:52`) | "always entered by hand, via the Dashboard's Transactions tab or Recurring Transactions Config" | Contributions are also created from the Goals tab (Add contribution, split tool). Recurring is excluded for Goals (section 5), so the sentence is only partly true for the Goals Category. |
| `GLOSSARY.md` **Savings**, **Category** (`:38`, `:52`) | Savings "starts predefined with two defaults, Savings and Investments" | Three, one locked. |
| ADR-0022 Consequences | Savings/Investments "must stay freely editable, unlike Beem Adjustment" and it rejects reusing `locked` for Savings | Goals is locked inside Savings. Not a contradiction of Savings/Investments, but an exception to "Savings Categories are editable". |
| `GLOSSARY.md` **Transaction Log** (`:68`) | Columns: "Date, Amount, Type, Category, Notes" | A sixth, nullable `goal_id`. Also "Amount (always positive...)" holds for contributions. |
| `GLOSSARY.md` **Database** (`:72`) | Lists the tables it holds | Add Goals. |
| ADR-0010, ADR-0021, `GLOSSARY.md` **Financial Year**, **Budget tab** (`:112`, `:148`) | Overview, Budget and Transactions share the switcher; Settings renders none | Goals is a fifth tab and "not tied to the Financial Year switcher". `App.jsx:324` shows the switcher for every tab except Settings and would need Goals excluded; `periodAnchorFor` (`:237`) likewise. |
| ADR-0010 | Transactions tab is one year, filtered client-side | Goal totals are all-time, so they cannot come from this endpoint. |
| ADR-0009 / ADR-0011 | Overview content follows the mockup; Overview is month/Full-year scoped | A Goals tile on Overview that is "active Goals only" is not scoped to the selected period. |
| `docs/agents/statement-export-pipeline.md:98` | "A pair the backend may not assign (Savings, locked Categories)..." | Still true; no change. |

**Extends (consistent, but should be recorded):**

- ADR-0015 / `Category.locked` (first user: Beem Adjustment): a second locked Category. The doc comments hard-code "Beem Adjustment today".
- ADR-0022 (Savings is manual-only, AI-excluded) and ADR-0026 (History Matches never assign Savings): reinforced.
- ADR-0023 (Category Budget on Savings): Goals gets budgetable for free.
- ADR-0025 (migrations): first migration that adds a column to an existing table since `categories_table`; its "Consequences" cover table-additive work only implicitly.
- ADR-0030 / GLOSSARY **Backup**: unchanged; the "complete Database" claim stays true.
- ADR-0018 / `GLOSSARY.md` **Dashboard** (`:100`): a Goals tab is Dashboard-only, consistent.
- Term "Goal" / "contribution" is new to the glossary (searched `GLOSSARY.md`, `docs/adr/`, `src/`, `frontend/src/`, `tests/`: no prior use; the one hit is a comment in `BalanceStatus.jsx:25`).
- Candidate ADR number: next free is 0031 (`docs/adr/` ends at 0030).

## 12. Test and fixture impact (for the spec's checklist)

- `tests/conftest.py:25-35` (`_DEFAULT_CATEGORIES`, hard-codes the locked name) and `FakeStore` (`:63`) must mirror `LocalStore` for `goal_id` and Goals.
- `tests/transaction_log/test_categories.py:29`: pins Savings Categories.
- `tests/migration/test_registry.py:10-14`: pins the migration list.
- `frontend/src/App.test.jsx:1934`: tab list.
- `tests/dashboard/test_transactions_api.py:407-421`, `:485-502`: Import template and commit exclude locked Categories; Goals will be covered by the same assertions.
- Wire-shape tests for `/api/transactions`, `/api/categories` (`tests/dashboard/test_categories_api.py:50-65` lists locked flags).

## Not verified

- Live-data collisions (an existing user-made "Goals" Category, any Savings rows that should become contributions): not read; see section 8.
- SQLite `COLLATE NOCASE` behaviour is from general knowledge of the SQLite docs, not retrieved here.
- `docs/Todo.md`, named in the map, is not tracked in this repo (not in `git ls-files`), so the "Plan area" line was not checked.
