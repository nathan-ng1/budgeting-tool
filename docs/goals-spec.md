# Goals tab: implementation spec

Ready to hand to `/implement`. Assembled from the wayfinder map (issue #207) and its closed tickets. Vocabulary is in `GLOSSARY.md` (Goal, Contribution, Past goals, Goals tab, Locked Category); the reasoning for the data model is [ADR-0031](./adr/0031-goals-are-a-locked-savings-category-linked-to-transactions.md).

References:
- Code audit: [`docs/research/goals-audit.md`](./research/goals-audit.md). File and line pointers below are from commit `7b6c8a8` and will drift; re-check before editing.
- Clickable prototype (throwaway, **not for merge**): branch `prototype/goals-tab`, code in `frontend/src/prototype/goals/`. Run `npm run dev` in `frontend/` (plus `uv run python -m dashboard` for the Overview tile) and open `/?variant=A`. Its `goalsMath.js` is a working reference for status, pace, months and cent allocation, but it is client-side and stubbed: the real build computes all of it on the server.

## 1. What is built

A fifth Dashboard tab, **Goals**, plus an Overview tile. A **Goal** is a savings target with a required end date. A **Contribution** is an ordinary Savings-Type Transaction in a new locked Category **Goals**, linked to its Goal. Everything else about Goals is derived from those Contributions.

## 2. Data model

### 2.1 `goals` table (new)

| Column | Notes |
| --- | --- |
| `id` | integer primary key |
| `title` | required; trimmed |
| `description` | nullable |
| `target_amount` | `REAL`, like `transactions.amount`; must be > 0 |
| `start_date` | ISO text; defaults to today in the UI; may be past or future |
| `end_date` | ISO text; required |
| `state` | `active` / `archived` / `deleted` (lifecycle only) |

No archive/delete timestamps. Status (Upcoming, Active, Achieved, Ended), saved amount, pace and On track/Behind are **derived**, never stored. An Achieved Goal stays `state = active` until the user archives it.

**Title uniqueness** (trimmed, case-insensitive, across all states including archived and deleted) is checked **in code** using Python `casefold()`, not by a database constraint (SQLite's `lower()` and `NOCASE` only fold ASCII, and Category names already use code-level checks).

Add `goals` to `SCHEMA` (`src/database/store.py`) as `CREATE TABLE IF NOT EXISTS`.

### 2.2 `transactions.goal_id` (new column)

Nullable integer, `REFERENCES goals(id)` (documentation only; foreign keys are not enforced in this codebase). Add it to the `transactions` `CREATE TABLE` in `SCHEMA` for new installs. Do **not** add an index on it in `SCHEMA` (see 3).

Extend `Transaction` (and `Candidate` where needed, `src/transaction_log/entries.py`) with a trailing `goal_id: int | None = None` so existing keyword constructions stay valid (`store.py:170`, `:532`, `tests/conftest.py:296-309`).

### 2.3 The Goals Category (new, predefined, locked)

A Savings-Type Category named `Goals`, `locked = 1`, seeded with a fixed emoji 🎯. The emoji is a seed value only: a locked Category can't be edited.

Replace the hard-coded `name == "Beem Adjustment"` lock check (`store.py:585`, mirrored in `tests/conftest.py:26`) with **one small table of locked predefined Categories and their emoji** in `transaction_log/categories.py` (Beem Adjustment: locked, no emoji; Goals: locked, 🎯), used by the seed, the test `FakeStore`, and the migration, so they cannot drift. Add `Goals` to `CATEGORIES_BY_TYPE["Savings"]` so it counts as predefined everywhere (including `count_data`'s "custom Categories" count). Update the doc strings that say "Beem Adjustment today" (`categories.py:8`, `:145`; `store.py:101`; `history.py:106`).

## 3. Migration (ADR-0025)

One new registry entry appended to `MIGRATIONS` in `src/migration/registry.py`: **`add_goals`**, in `src/migration/add_goals.py`, exposing `migrate(connection)`. Three guarded steps, in this order, so a rerun after a failure resumes cleanly:

1. `CREATE TABLE IF NOT EXISTS goals ...`. The migration must create the table itself: database move runs migrations before `open_connection` applies `SCHEMA` (`src/dashboard/database_move.py:226-232`).
2. `ALTER TABLE transactions ADD COLUMN goal_id INTEGER`, behind a `PRAGMA table_info` check (pattern: `categories_table._migrate_table`). Create any index on `goal_id` here, **not** in `SCHEMA`: `SCHEMA` also runs against old files and would raise where the column doesn't exist yet.
3. The Goals Category, matched **case-insensitively by name**:
   - No match: insert a locked `Goals` under Savings with the emoji.
   - A match under Savings with **no rows** (no Transactions, no Recurring rules): adopt it (set locked, set the emoji).
   - Any other match (it has rows, or it is under another Type): **fail** with a message naming the Category and asking the user to rename it in Category Management. The runner leaves a failed migration unrecorded, and `python -m migration` makes a `pre-migration` copy first.

Append only, never reorder. A brand-new Database marks every entry applied without running it. Any later migration that rebuilds `transactions` must copy `goal_id`.

**Startup guard.** `src/dashboard/__main__.py` opens the Database with a bare `connect()`. Add a check for pending migrations (`migration.runner.pending`) that **refuses to start** with a clear message to run the update first (`update.bat` / `update.command`). It does not run migrations itself (ADR-0019). Without it, a code pull without an update fails every Transactions read once `goal_id` is selected.

Live-data check (#211, 2026-10-14): the maintainer's Database has no Category with "goal" in its name and no Savings rows, so the migration's adopt and fail paths are not exercised by it.

## 4. Store rules (enforced in the store, not only the frontend)

On every create and update of a Transaction:

1. `goal_id` is non-null **if and only if** Category = Goals. A Goals row without a `goal_id`, and a `goal_id` on any other Category, are rejected.
2. The Goal must exist.
3. A **new** link, or moving a row to a **different** Goal, requires the target Goal to be `active`. A row may keep its existing link if that Goal is now archived or deleted, so editing its Notes or date still works.
4. Changing a row's Category away from Goals is only valid when the payload sends `goal_id` null. The frontend does this automatically; the store rejects anything else (`update_transaction` is a full-row replace and would otherwise keep a stale `goal_id`). `withType` in `frontend/src/lib/transactionForm.js` already resets the Category when Type changes and must clear a stale Goal too.

Violations are `ValueError`s, which the server maps to 400 (`src/dashboard/server.py:380-399`).

**Recurring exclusion.** The Recurring Transactions Config form omits the Goals Category (it currently uses `groupByType` with no `locked` filter: `RecurringRules.jsx:74`, `:284`; `ruleForm.js:69`). `create_recurring_rule` and `update_recurring_rule` also reject it, through **one named predicate** in the store (for example `is_goals_category`), not a new flag on categories. The Transactions form must still offer Goals, so a generic `locked` filter in `groupByType` is wrong. Beem Adjustment's existing presence in the Recurring dropdown is a separate gap and is left alone.

**Dedupe.** Contributions created from the Goals tab and by the split tool insert directly with **no dedupe**, like manual Transactions-tab adds (which never go through `resolve_writes`). Two identical Contributions are both kept. Do not route them through `resolve_writes`.

**CSV Export** stays at five columns. A Goals row exports but Import refuses it (locked), consistent with Beem Adjustment. **Import** needs no change.

## 5. Transactions tab

- Category = Goals reveals a **required Goal picker**, in the add form and in the in-row editor (both share `useTransactionEditor`, `Transactions.jsx:495-526`; the conditional-extra precedent is `BILLS_HINT`, `:531`, `:542`). Options: active Goals, plus the row's current Goal when editing.
- If there are no active Goals, **Goals stays visible in the Category dropdown but disabled**, labelled "(no active Goals)", so the Category isn't mysteriously missing.
- **Notes** default to the Goal's title when **adding** a row, editable. On **edit**, Notes are never auto-rewritten, which avoids the dedupe hazard in ADR-0031.
- **Re-pointing:** editing a Savings or Investments row to Category = Goals plus a Goal re-points it. Moving back to Savings/Investments clears `goal_id`. Changing the Goal while staying on Goals moves the Contribution.
- **Goal chip:** Goals-Category rows show the linked Goal's **current** title as a chip (in the Category cell, `Transactions.jsx:412`). Past goals show muted with "(archived)" or "(deleted)". Not clickable.
- Wire shape: add a nullable `goal_id` and the Goal's title to `as_payload` / `from_payload` (`src/dashboard/transactions.py:46-54`, `:149-170`), the `Transaction`/`Candidate` dataclasses, `read_transactions`' JOIN (`store.py:164-179`), `create_transaction`, `update_transaction`, `toPayload` (`transactionForm.js:36`) and `transactionsApi.js:47-53`.
- Editing or deleting an individual Contribution happens here: the Goals tab's Details view is read-only.

## 6. Category Management and Budget

- Goals shows the lock with a **Goals-specific tooltip** ("managed by the Goals tab"). The existing lock logic (`CategoryManagement.jsx:157`, `:175`) already hides rename/delete/emoji editing.
- **Category Budget on Goals is allowed, unchanged.** It appears in the Budget editor, Budgeted vs Actual and Left to Budget with no code change: a monthly allowance for Contributions overall, distinct from each Goal's own required-per-month. Budget Suggestion drops Savings already (`budget_suggestions/run.py:35`).
- The categorisation backend, History Match and Needs Review exclude Goals with no change (Savings is in `AI_EXCLUDED_TYPES`; Goals is locked). Contributions never become prompt examples.

## 7. Goals endpoint and derived figures

One **server-side** Goals endpoint returns, for every Goal: its fields, `state`, saved amount (sum of **all** linked Contributions, all-time), Status, pace and On track/Behind, months remaining, required per month, original plan, and a Contributions ledger for the Details view. The Overview tile reads the same endpoint and takes the top three. Transactions loads one Financial Year (ADR-0010), so these figures cannot come from that endpoint. All figures are computed against a **single "today"** so the tab and tile always agree. The frontend only formats, following the Date Order and Display Currency settings.

Rules (the prototype's `describeGoal` in `goalsMath.js` implements these and may be copied as a reference):

- **Saved** = sum of linked Contributions, regardless of date, including Contributions to archived or deleted Goals. Overshoot is allowed.
- **Status**, in this precedence: **Achieved** (saved >= target), else **Ended** (today after the end date), else **Upcoming** (today before the start date), else **Active**.
- **Months**: calendar months elapsed from the start date's day, a partial month rounded up, minimum 1 (20 Oct to 20 Dec = 2, 20 Oct to 21 Dec = 3, 20 Oct to 5 Nov = 1). A start day past the end of a shorter month clamps to that month's last day (31 Jan to 28 Feb = 1).
- **Required per month** = (target - saved) / months from **today** to the end date (so Upcoming Goals count from today). Not shown once Achieved or when the end date has passed.
- **Original plan** hint = target / months from start to end date (same counting).
- **Pace** = target spread evenly by days from start to end date; the pace marker sits at 0 until the start date and at the target from the end date. **On track** = saved >= pace (a half-cent tolerance), else **Behind**. On track/Behind is only meaningful while a Goal is Active.
- **Past goals** (`state` archived or deleted) are returned separately, with a badge value, and are excluded from the Overview tile.

### 7.1 Goal actions

- **Create / edit** (title, description, target, start, end). Reactivating a Past goal opens the same pre-filled edit form and sets `state` back to `active`.
- **Archive** and **Delete** both set `state` (soft) and move the Goal to Past goals. There is no permanent delete. Contributions are never touched. An Ended Goal stays in the main list until acted on.

## 8. Contributions from the Goals tab

- **Add contribution** (per-Goal button): amount, date, Notes defaulting to the Goal's title. Writes a Goals-Category Savings Transaction linked to that Goal.
- **Split savings** (see 9).

## 9. Split tool

- Inputs: **total** (prefilled from the selected month's Unallocated when positive, editable), **date**, a **percentage per active Goal** (prefilled from the last-used split, a prefill not a standing rule), a **remainder** row with a Savings/Investments Category picker. The sum of Goal percentages is hard-capped at 100% with an inline error.
- Shows a live preview of the exact Transactions it will write, then a one-line confirmation.
- Writes one Contribution per Goal with a non-zero share. Whatever is left of 100% is written as one Savings-Type Transaction in the chosen Category (Savings or Investments). If Goals take exactly 100%, **no remainder row** is written.
- **Atomic:** one store method writes every row in a **single SQLite transaction** (`append_rows` takes Candidates with no `goal_id`, and `create_transaction` commits per call). The **server computes the allocation** from percentages; it does not trust client-sent amounts.
- **Cents:** largest-remainder method. Floor each share to the cent, then give the leftover cents to the largest fractional parts, so rows sum exactly to the total and the same inputs always give the same rows. The existing `recurring.split_from_payload` (ROUND_HALF_UP, accepts drift) is a pattern, not a reuse.
- The remainder row's Notes should be distinct from any Goal's Notes so the two can never collide under a later dedupe.
- Last-used percentages are remembered as a prefill; where they are stored is an implementation choice (see 15).

## 10. Goals tab UI (Variant A, from the prototype)

- Header: Goals summary, **Split savings** and **New goal** buttons. No Financial Year switcher: exclude the Goals tab from the switcher and `periodAnchorFor` in `App.jsx` (`:324`, `:237`).
- **Card grid.** Each card: title, status chip (On track / Behind / Achieved / Ended / Upcoming), optional description, the monthly figure as the headline ("Save $X / month, to finish by <end date> (N months left)"), a progress bar with the even-pace tick, "saved of target" and %, and the "Original plan: $Y / month" hint. One button row: Add contribution, Edit, Archive, Delete; **Details** as a full-width primary button on its own row below.
- **Details view** (replaces the grid in place; filled accent "← All goals" button top right; status chip beside the title): stats (Needs / month as the headline, then Saved of target, Left, Remaining time, End date, Original plan, Start date); a **dot-to-dot trajectory chart** (a marked point per Contribution at the running total, carried flat to today; gridlines, y-axis dollar ticks, x-axis month ticks with the start and end dates, axis titles "Amount saved" and "Date", labelled in place with Target, Even pace, Saved, Today, no legend); and a **Contributions ledger** (Date / Notes / Amount, header row like the Dashboard's other tables, about 460px wide). **Read-only**: no actions on this page.
- **Split panel** slides down from the Goals tab header.
- **Past goals:** a collapsed list with an Archived / Deleted badge, saved of target and **Reactivate**.
- The prototype uses a fixed `en-AU` date format and stubbed numbers (for example Unallocated $1,240). The real build follows the Date Order and Display Currency settings and reads the actual Unallocated.

## 11. Overview tile

Up to the **top three active Goals** (soonest end date first): title, status chip, bar with pace tick, "% funded" and "$X / month". The header shows the count of active Goals, with a "View all goals" link. An empty state when there are none. No Unassigned line. Not scoped to the selected period (a deliberate exception to ADR-0009/0011).

## 12. Unchanged figures

The Saved tile, Available to Save and Unallocated are unchanged: the Goals Category sits under the Savings Type, so Contributions count there already.

## 13. Reset, Backup and Database move

- **Reset** rebuilds the Database from `SCHEMA` plus the seed (`database_reset.py:65-107`), so the `goals` table and the Goals Category return on their own. Add a **Goals count** to `LocalStore.count_data` (`store.py:490-507`; every Goal, any `state`) and one line to the lost-data list in `frontend/src/components/DeleteData.jsx:99-103`. The Goals Category is predefined, so it is not a custom Category. Contributions are already counted as Transactions.
- **Backup** copies the whole file and needs nothing. **Database move / switch** is handled by the migration registry for older or newer files and needs nothing.

## 14. Retail Edition

Parity by construction: everything Goals adds lives in `database/`, `migration/`, `transaction_log/`, `dashboard/` and `frontend/`, which the Retail Edition includes. **Rule: Goals code must not import from the packages Retail excludes** (categorisation, statement export, advisor, budget suggestion). `docs/retail-edition-design-notes.md` is left untouched.

## 15. Assumptions made while assembling this spec

These were not decided in a grilling ticket. Confirm or change them during implementation:

- Validation: target > 0; end date on or after start date; Contribution amounts positive. (The prototype treats a zero-length window as one day.)
- Where the last-used split percentages are stored (the prototype keeps them in memory; real options are a Display Settings-style row or browser storage).
- API route names, payload shapes and the exact error messages.
- Cent rounding applies to the total in cents (`round(total * 100)`).
- Section 16: the dashboard guide and README tab count are updated in the feature PR, not at release (only the changelog entry waits for release).
- The Goals tab's tab position: placed after Transactions and before Budget or Settings is an implementation call; the glossary lists it as a fifth tab without fixing the order.

## 16. Docs updated with the feature (not at release)

- `docs/dashboard-guide.html`: "four tabs" (`:143`) becomes five; add a Goals card (`:176-224` pattern); the Overview card (`:180-196`) needs the Goals tile; the Transactions card (`:198-204`) needs the Goal picker and chip; the Settings card (`:215-223`) says a locked Category "can't be renamed or deleted", which Goals now joins. Add a "How to use?" step if it fits (`:163-174`).
- `README.md:278` "the four tabs".
- **Not** the changelog: `CHANGELOG.md` has no Unreleased section (ADR-0029); the Goals entry is written at release time on `chore/release-X.Y.Z`.

## 17. Test and fixture checklist

From the audit (section 12), plus the new behaviour:

- `tests/conftest.py:25-35` (`_DEFAULT_CATEGORIES`, hard-codes the locked name) and `FakeStore` (`:63`) must mirror `LocalStore` for `goal_id` and Goals.
- Pinned lists that fail by design: `tests/transaction_log/test_categories.py:29` (Savings Categories), `tests/migration/test_registry.py:10-14` (migration names; also extend the "pre_categories_table" chain test), `frontend/src/App.test.jsx:1934` (tab names).
- Import tests (`tests/dashboard/test_transactions_api.py:407-421`, `:485-502`) already cover locked Categories; Goals is covered by the same assertions. Wire-shape tests for `/api/transactions` and `/api/categories` (`tests/dashboard/test_categories_api.py:50-65` lists locked flags). Reset: `tests/dashboard/test_database_reset_api.py`, `tests/database/test_store.py`.
- New: the four store rules in 4; Recurring rejection; the `add_goals` migration (fresh, existing without a clash, adopt-empty-Savings-Category, fail on a clash, rerun after partial failure); startup refusal with pending migrations; every status and edge of the figures in 7 (Upcoming, Achieved precedence over Ended, min one month, zero-length window); split allocation (cents sum exactly, determinism, 100% cap, no remainder row at exactly 100%, atomic rollback); title uniqueness across Past goals; reactivation.

## 18. Out of scope

- Recurring contributions (a Recurring Transactions Config rule that targets a Goal); the data model leaves room.
- Withdrawals from a Goal (Savings Transactions are always positive).
- Forecasting and any wider "Plan" area.
- Version History entry (written at release time).
