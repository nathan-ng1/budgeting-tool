# Budgeting Tool

A personal, manually-triggered process that turns credit card statement exports into categorised
entries in a local budget database, viewed and managed through a Dashboard.

## Language

**Statement Export**:
A raw CSV file downloaded from a card issuer's online banking and dropped into `.data/`, named `{Issuer}_{yyyymmdd}.csv` (e.g. `ANZ_20260730.csv`). Contains one row per Transaction, no header row.
_Avoid_: Raw CSV, transaction file

**Transaction**:
A single row within a Statement Export: a date, a signed amount (negative = spend, positive = Bill Payment or Refund — see those terms), and a merchant description.
_Avoid_: Line, entry, record

**Beem Report**:
A CSV export from the Beem P2P payment app, dropped into `.data/` following the same `{Issuer}_{yyyymmdd}.csv` naming convention as a Statement Export (e.g. `Beem_20260730.csv`). Distinct from a Statement Export: it has a header row, and each row's sign is bidirectional — derived from whether the user was Payer or Recipient, not a fixed sign-per-column convention. An incoming Beem Transaction (money to the user) is a reimbursement for a shared or prior Expense, not standalone earning — it's written to the Transaction Log as Type Expense, Category Beem Adjustment, with a negative Amount that reduces Expense totals rather than as Income. See [ADR-0015](./docs/adr/0015-beem-adjustment-reduces-expense-instead-of-income.md).
_Avoid_: Beem export, Beem statement

**Bill Payment**:
A positive-Amount row on a card Statement Export that pays down the card balance rather than crediting a purchase back. Every positive-Amount card row is unconditionally a Bill Payment — dropped from processing entirely: never categorised, never written to the Transaction Log, never a per-transaction judgement call. See [ADR-0016](./docs/adr/0016-retire-refund-positive-amount-card-rows-are-always-bill-payment.md) (superseding [ADR-0007](./docs/adr/0007-classify-refunds-vs-bill-payments-via-the-categorisation-backend.md), which used to classify these against Refund).
_Avoid_: Payments & Refunds (old blanket term for every positive-Amount row, retired now that they're classified individually), Refund (retired Category — see ADR-0016; a merchant credit is instead handled by removing or adjusting the original Expense Transaction), Credit, Payment

**Sanitising**:
An issuer-specific step that strips personal information from a Statement Export before it's processed further. Runs as a Python script, never as something Claude does directly — see [ADR-0001](./docs/adr/0001-sanitising-happens-outside-claudes-read-access.md). For ANZ, sanitising is a no-op: ANZ exports contain no personal identifiers (no name, account number, or card number). For NAB, sanitising drops the Account Number, Balance, and NAB's own Category columns, and collapses Merchant Name/Transaction Details into a single Notes field (falling back to Transaction Details when Merchant Name is blank) — the raw NAB export is not itself in the 3-column Statement Export shape.
_Avoid_: Cleaning, scrubbing

**Type**:
The top-level classification of a Transaction: Income, Expense, Debt, or Savings. Every Category has exactly one fixed Type. Replaces what was previously called "Category" — see [ADR-0006](./docs/adr/0006-simplify-to-three-types-with-a-flat-category-list.md).
_Avoid_: Category (retired for this meaning), Group, Real Income (Dashboard tile copy for the Income Type — no distinct concept, just "Income")

**Category**:
The specific budget label for a Transaction — e.g. Groceries, Subscriptions, Salary. Flat: there's no grouping layer between Category and Type (the old Bills & Subscriptions / Expenses / Debt / Savings / Investments split is gone). Each Category has one fixed Type, never determined per-Transaction:
- **Income**: Salary, Rental
- **Expense**: Groceries, Dining & Takeaway, Transport, Shopping & Retail, Holidays & Travel, Entertainment & Leisure, Health & Medical, Donations & Giving, Subscriptions, Insurance & Bills, Rental Expense, Beem Adjustment
- **Debt**: Mortgage Repayment — populated lazily like Rental and Rental Expense above; the first real non-mortgage Debt (e.g. a car or personal loan) adds its own Category rather than one being speculatively predefined. Unlike Savings below, no further Categories are predefined ahead of a real case.
- **Savings**: Savings, Investments — predefined for every install rather than populated lazily, the only Type given this exception; see [ADR-0022](./docs/adr/0022-rename-transfer-to-savings-with-predefined-categories.md).

Every categorised Transaction gets exactly one Category, which determines its Type. Replaces what was previously called "Sub-category" — see [ADR-0006](./docs/adr/0006-simplify-to-three-types-with-a-flat-category-list.md).
_Avoid_: Sub-category (retired), Label, tag

**Subscriptions** (Category):
Means the Transaction *itself* is a recurring charge (same merchant, regular cadence — e.g. the Anthropic Claude charge), not "sold by a platform that also offers subscriptions." A one-off purchase from a subscription-style platform (e.g. a single Steam game purchase) goes by what was bought, landing in Entertainment & Leisure instead.
_Avoid_: Label, tag, Bill (a Bill is a Transaction whose Category maps to a bill-like Expense, not a Category name itself)

**Debt**:
A Transaction that services a borrowing you owe to a lender — reducing the outstanding balance of a loan, including any interest bundled into the same repayment (the Statement Export carries no principal/interest split, so the whole repayment is Debt). One of the four Types, alongside Income, Expense, and Savings. Distinct from an Expense (money consumed) and from Savings (money moved to an account you own): a Debt repayment converts cash into equity you hold in an asset, but unlike Savings it is non-discretionary and its counterparty is external. Previously folded into Expense — see [ADR-0006](./docs/adr/0006-simplify-to-three-types-with-a-flat-category-list.md) — split back out by [ADR-0012](./docs/adr/0012-split-debt-back-out-of-expense.md).
_Avoid_: Liability, Loan repayment

**Savings**:
A Transaction that moves money to an account you own and control (a savings or investment account) rather than to a third party. Looks identical to an Expense in a bank export — a debit leaving the account — but is economically distinct: not consumption. One of the four Types, alongside Income, Expense, and Debt. Its Category list starts predefined with two defaults, Savings and Investments — the Savings Category shares its name with the Savings Type, a deliberate overlap rather than a naming mistake — the only Type given predefined Categories rather than lazy population, since (unlike Debt, which varies person to person) every user has some form of savings or investment account. Never assigned by the categorisation backend or offered in Needs Review: a Savings Transaction is always entered by hand, via the Dashboard's Transactions tab or Recurring Transactions Config, never from a Statement Export. See [ADR-0022](./docs/adr/0022-rename-transfer-to-savings-with-predefined-categories.md), which renames this Type from Transfer and supersedes ADR-0006's lazy-population policy for it.
_Avoid_: Transfer (this Type's retired name — see ADR-0022)

**Transactions Inbox**:
The external folder (path set via `TRANSACTIONS_INBOX` in `.env`) where unsanitised Statement Exports are saved directly from a card issuer's site. Claude never reads this location — only the Sanitising script does.
_Avoid_: Raw folder, landing directory, local directory

**Transaction Log**:
The database table this process writes to. One row per categorised Transaction: Date, Amount (always positive, two decimal places, regardless of the Statement Export's sign — except Category Beem Adjustment, a deliberate, narrow exception stored negative so it reduces Expense totals, see [ADR-0015](./docs/adr/0015-beem-adjustment-reduces-expense-instead-of-income.md)), Type, Category, Notes (the merchant description carried over from the Statement Export). Before writing, each Transaction is checked against existing Transaction Log rows (matching Date + Amount + Notes) and skipped if already present, since Statement Export date ranges can overlap between runs. A row can also be added directly (not just via Statement Export or Recurring Transaction expansion) through the Dashboard's Transactions tab, which offers full add/edit/delete over the Transaction Log; such a row is checked against the same Date + Amount + Notes dedupe as any other on the next Statement Export run. Previously a Google Sheets tab — the Sheet is retired as the live store, see [ADR-0005](./docs/adr/0005-migrate-transaction-log-and-recurring-config-to-a-local-database.md).
_Avoid_: Budget sheet, spreadsheet, Google Sheet, Description (for the Notes field — Notes is the term everywhere it appears, including the Dashboard's Transactions tab)

**Needs Review**:
The checkpoint where the configured categorisation backend flags every Transaction it can't confidently assign a Category to (a `needs_review` flag in its structured response), and `uv run python -m statement_export` prompts you for each one right in the terminal. Nothing is written to the Transaction Log until every Needs Review item for that file is resolved.
_Avoid_: Uncategorised, low-confidence

**Processed archive**:
`.data\processed\` — where a Statement Export moves once its Transactions have been successfully written to the Transaction Log. Anything still sitting directly in `.data\` is outstanding and hasn't been processed yet.
_Avoid_: Archive, done folder

**Recurring Transactions Config**:
A database table — one row per predictable, known-in-advance recurring item (salary, mortgage payments, etc.), independent of any Statement Export. Columns: Amount, Type, Category, Notes, Frequency (Weekly/Monthly), Interval (every N periods), Day (day-of-week for Weekly, day-of-month for Monthly — clamped to the last day of the month if it doesn't exist, e.g. Day=31 in February), Start Date, End Date (optional — blank means recurs indefinitely). Editable via the Dashboard. Previously `config\recurring-transactions.xlsx`, hand-edited outside Claude — retired, see [ADR-0005](./docs/adr/0005-migrate-transaction-log-and-recurring-config-to-a-local-database.md).
_Avoid_: Recurring config, schedule file, .xlsx

**Recurring Transaction**:
A single occurrence generated by expanding a Recurring Transactions Config rule's schedule from its Start Date through today. Expansion is done by a deterministic script, not Claude — see [ADR-0002](./docs/adr/0002-recurring-schedule-expansion-happens-in-a-script.md). Generated occurrences go through the same Needs-Review-free path straight to dedupe (Date + Amount + Notes against the Transaction Log) and are written if not already present — the full history is re-expanded and re-checked every run rather than tracking a separate "last run" cursor. Triggered one of two ways, both expanding through the same target date (today) and sharing identical dedupe: automatically as part of `process_statement_export` (a Statement Export run always expands every rule too, not just the file's own rows), or manually via the "Run now" button on the Dashboard's Recurring Transactions Config screen — for a user without a Statement Export pipeline to run (see [ADR-0018](./docs/adr/0018-non-ai-path-is-dashboard-only.md)), but available unconditionally to any user, since the Dashboard has no runtime concept of an AI-enabled install.
_Avoid_: Scheduled transaction, generated transaction

**Dashboard**:
The local web app that's the primary interface for viewing budget data and editing the Recurring Transactions Config — replaces Google Sheets as the interface. Runs locally (a small backend plus a browser frontend) against the local database; Transaction data never leaves the machine. Does not handle Needs Review resolution (that stays the terminal prompt flow) or Statement Export processing — those remain scripted, chat-adjacent flows separate from the Dashboard. See [ADR-0008](./docs/adr/0008-dashboard-is-a-local-web-app-not-a-hosted-artifact.md).
_Avoid_: UI, frontend, web app, spreadsheet

**Financial Year**:
The July 1–June 30 window the Dashboard's Overview, Budget, and Transactions tabs can be organised around — the default framing, and one of the two options on the Financial Year/Calendar Year switcher shared across those three tabs (see [ADR-0021](./docs/adr/0021-financial-year-switcher-and-calendar-year-toggle.md)). Its selector shows the twelve months of one Financial Year plus a Full year option, matching the Australian financial year convention already implicit in this project's card issuers (ANZ, NAB).
_Avoid_: FY

**Calendar Year**:
The January 1–December 31 window — the switcher's other framing, alongside Financial Year (see [ADR-0021](./docs/adr/0021-financial-year-switcher-and-calendar-year-toggle.md)). Reorders the twelve month pills to run Jan→Dec and changes what "Full year" aggregates, but doesn't change how any individual month's figures are computed.
_Avoid_: CY

**Full year**:
The Overview tab's other selector state, alongside a specific month: aggregates every Transaction in the active Financial Year or Calendar Year to date, rather than one month. The Dashboard's default view on open. For the current, in-progress year, "to date" means elapsed months only, including the current month before it's finished — a month that hasn't happened yet contributes $0, it isn't skipped. See [ADR-0011](./docs/adr/0011-full-year-overview-is-a-selector-state-not-a-tab.md). The Budget tab reuses the same pill and label for its own, differently-scoped Full year state — see Budget tab, below.
_Avoid_: Annual Overview, Year view, Yearly

**Net Balance**:
A Dashboard stat tile: `Income − Expenses − Debt` for the period shown. Money moved to Savings is never subtracted, so it still counts toward this figure — Net Balance includes what's been saved, not just what's left in spendable cash, since a Savings Transaction is money moved to an account you still own, not spent or earned. See [ADR-0009](./docs/adr/0009-overview-tab-scope-follows-the-approved-mockup.md) and [ADR-0012](./docs/adr/0012-split-debt-back-out-of-expense.md) (which added the `− Debt` term when Debt split out of Expense), and [ADR-0022](./docs/adr/0022-rename-transfer-to-savings-with-predefined-categories.md) (renamed Transfer to Savings and corrected the Dashboard's subtext from "excludes transfers" to "includes savings" to match this, unchanged, formula).
_Avoid_: Net income, Surplus, Cash flow

**Category Budget**:
A user-set target Amount for one Category in one specific month — every month stands alone, edited and kept independently of every other month, with no averaging or carry-forward between them. Applies to any Income, Expense, or Debt Category (Savings has none to budget). A Category with no Category Budget set for a given month is unbudgeted for that month, not budgeted at $0. Compared against that Category's actual for the same month on the Dashboard's Budgeted vs Actual table, which partitions its rows by Type. See [ADR-0009](./docs/adr/0009-overview-tab-scope-follows-the-approved-mockup.md) (introduced the concept, originally Expense-only and month-invariant) and [ADR-0013](./docs/adr/0013-category-budget-is-per-month-across-income-expense-and-debt.md) (made it per-month and extended it to Income/Debt).
_Avoid_: Budget (too vague — always means Category Budget in this project), Target, Limit, Expected (the Dashboard's original column label for this value, retired in favour of Budgeted once the label and the concept's name matched)

**Budget tab**:
The Dashboard tab (alongside Overview, Transactions, Settings) for setting Category Budgets one Financial Year month at a time and reviewing the current Budget Suggestion. Picks up the shared Financial Year/Calendar Year switcher (Overview's since [ADR-0021](./docs/adr/0021-financial-year-switcher-and-calendar-year-toggle.md)) in a later ticket. Its month selector also offers a Full year pill showing a read-only 12-month × Category grid of everything budgeted across the active year — unlike the Overview tab's Full year, this grid is never restricted to elapsed months (a Category Budget set ahead for a future month still shows), since it is summarising budgets set, not aggregating actual Transactions to date. Selecting it offers no editing surface at all; editing only happens through an individual month pill. Both the per-month editor and the Full year grid show a Total row per Type, summing that Type's Budgeted Amount across its Categories (live, before Save, in the per-month editor). The per-month editor also offers an Auto-populate control next to Save budgets, wholesale-overwriting every Category's Budgeted Amount field (staged, not yet saved) from either last month's actuals or last month's own Category Budgets, mirrored exactly Category-by-Category — see Issue #77. Named as a later-phase placeholder as far back as [ADR-0008](./docs/adr/0008-dashboard-is-a-local-web-app-not-a-hosted-artifact.md) and left unwired through [ADR-0009](./docs/adr/0009-overview-tab-scope-follows-the-approved-mockup.md); built out by [ADR-0013](./docs/adr/0013-category-budget-is-per-month-across-income-expense-and-debt.md) (per-month editor), Issue #64 (read-only Full year grid), and Issue #77 (Auto-populate, Type Total rows).
_Avoid_: Budget screen, Budgeting tab

**Installation Pack**:
The `setup`/`update`/setup-guide bundle that takes a new user from nothing installed to a running Dashboard (and, if they hold an AI subscription, the Statement Export pipeline too) — `windows/setup.bat` + `windows/update.bat` + `docs/setup-guide.html` on Windows, `mac/setup.command` + `mac/update.command` + `docs/setup-guide-mac.html` on macOS (issue #117), both wrapping the same `src/setup` logic. `setup.bat`/`setup.command` is a standalone bootstrapper — runnable before Git or a clone exist — distributed as a GitHub Release asset; it branches on whether the user holds an AI subscription, since automated categorisation has no manual/null backend and so cannot be made to work without one. See [ADR-0017](./docs/adr/0017-installation-pack-is-a-bootstrapper-distributed-via-releases.md), [ADR-0018](./docs/adr/0018-non-ai-path-is-dashboard-only.md), [ADR-0019](./docs/adr/0019-update-checks-are-automatic-updates-are-manual.md).
_Avoid_: Installer, setup script (for the pack as a whole — `setup.bat`/`setup.command` is fine for the script itself)

**Budget Suggestion**:
A written analysis of how actual spend has tracked against Category Budgets recently, covering Expense and Debt Categories only (Income is excluded — under/over-earning isn't the kind of thing this advises on). One standing write-up at a time, not tied to any particular month: regenerating it replaces the previous write-up outright, no history kept. Produced by a scripted, deliberately non-interactive flow — the same shape as Categorising a Transaction (see [ADR-0004](./docs/adr/0004-categorisation-backend-is-pluggable-and-scripted.md)), not something triggered live from the Dashboard. See [ADR-0014](./docs/adr/0014-budget-suggestion-is-a-scripted-flow-not-a-live-dashboard-call.md).
_Avoid_: Budget advice, AI insights, Recommendation
