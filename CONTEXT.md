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
A CSV export from the Beem P2P payment app, dropped into `.data/` following the same `{Issuer}_{yyyymmdd}.csv` naming convention as a Statement Export (e.g. `Beem_20260730.csv`). Distinct from a Statement Export: it has a header row, each row's sign is bidirectional — derived from whether the user was Payer or Recipient, not a fixed sign-per-column convention — and it is Income-eligible: an incoming Beem Transaction is written to the Transaction Log as Income, not dropped the way a Bill Payment is.
_Avoid_: Beem export, Beem statement

**Bill Payment**:
A positive-Amount row on a card Statement Export that pays down the card balance rather than crediting a purchase back. Dropped from processing entirely: never categorised, never written to the Transaction Log. Distinguishing a Bill Payment from a Refund is a judgement call made by the categorisation backend (the same mechanism used for Category assignment), not a deterministic rule — see [ADR-0007](./docs/adr/0007-classify-refunds-vs-bill-payments-via-the-categorisation-backend.md).
_Avoid_: Payments & Refunds (old blanket term for every positive-Amount row, retired now that they're classified individually), Credit, Payment

**Refund**:
A positive-Amount row on a card Statement Export that's a merchant credit rather than a card balance payment (e.g. a returned purchase). Tracked as a real Transaction with Type Income and Category Refund — unlike a Bill Payment, which is dropped. See [ADR-0007](./docs/adr/0007-classify-refunds-vs-bill-payments-via-the-categorisation-backend.md).
_Avoid_: Credit, Payments & Refunds

**Sanitising**:
An issuer-specific step that strips personal information from a Statement Export before it's processed further. Runs as a Python script, never as something Claude does directly — see [ADR-0001](./docs/adr/0001-sanitising-happens-outside-claudes-read-access.md). For ANZ, sanitising is a no-op: ANZ exports contain no personal identifiers (no name, account number, or card number). For NAB, sanitising drops the Account Number, Balance, and NAB's own Category columns, and collapses Merchant Name/Transaction Details into a single Notes field (falling back to Transaction Details when Merchant Name is blank) — the raw NAB export is not itself in the 3-column Statement Export shape.
_Avoid_: Cleaning, scrubbing

**Type**:
The top-level classification of a Transaction: Income, Expense, or Transfer. Every Category has exactly one fixed Type. Replaces what was previously called "Category" — see [ADR-0006](./docs/adr/0006-simplify-to-three-types-with-a-flat-category-list.md).
_Avoid_: Category (retired for this meaning), Group, Real Income (Dashboard tile copy for the Income Type — no distinct concept, just "Income")

**Category**:
The specific budget label for a Transaction — e.g. Groceries, Subscriptions, Salary. Flat: there's no grouping layer between Category and Type (the old Bills & Subscriptions / Expenses / Debt / Savings / Investments split is gone). Each Category has one fixed Type, never determined per-Transaction:
- **Income**: Salary, Beem Adjustment, Rental, Refund
- **Expense**: Groceries, Dining & Takeaway, Transport, Shopping & Retail, Holidays & Travel, Entertainment & Leisure, Health & Medical, Donations & Giving, Subscriptions, Insurance & Bills, Rental Expense, Mortgage Repayment
- **Transfer**: none yet — Categories here are only added for real cases as they occur (e.g. a transfer to a specific savings or investment account), the same lazy-population policy Rental and Rental Expense already followed.

Every categorised Transaction gets exactly one Category, which determines its Type. Replaces what was previously called "Sub-category" — see [ADR-0006](./docs/adr/0006-simplify-to-three-types-with-a-flat-category-list.md).
_Avoid_: Sub-category (retired), Label, tag

**Subscriptions** (Category):
Means the Transaction *itself* is a recurring charge (same merchant, regular cadence — e.g. the Anthropic Claude charge), not "sold by a platform that also offers subscriptions." A one-off purchase from a subscription-style platform (e.g. a single Steam game purchase) goes by what was bought, landing in Entertainment & Leisure instead.
_Avoid_: Label, tag, Bill (a Bill is a Transaction whose Category maps to a bill-like Expense, not a Category name itself)

**Transfer**:
A Transaction that moves money to an account you own and control (a savings or investment account) rather than to a third party. Looks identical to an Expense in a bank export — a debit leaving the account — but is economically distinct: not consumption. One of the three Types, alongside Income and Expense; replaces the old Savings and Investments Categories.
_Avoid_: Savings, Investment (retired as top-level Categories — Transfer is the umbrella now)

**Transactions Inbox**:
The external folder (path set via `TRANSACTIONS_INBOX` in `.env`) where unsanitised Statement Exports are saved directly from a card issuer's site. Claude never reads this location — only the Sanitising script does.
_Avoid_: Raw folder, landing directory, local directory

**Transaction Log**:
The database table this process writes to. One row per categorised Transaction: Date, Amount (always positive, two decimal places, regardless of the Statement Export's sign), Type, Category, Notes (the merchant description carried over from the Statement Export). Before writing, each Transaction is checked against existing Transaction Log rows (matching Date + Amount + Notes) and skipped if already present, since Statement Export date ranges can overlap between runs. A row can also be added directly (not just via Statement Export or Recurring Transaction expansion) through the Dashboard's Transactions tab, which offers full add/edit/delete over the Transaction Log; such a row is checked against the same Date + Amount + Notes dedupe as any other on the next Statement Export run. Previously a Google Sheets tab — the Sheet is retired as the live store, see [ADR-0005](./docs/adr/0005-migrate-transaction-log-and-recurring-config-to-a-local-database.md).
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
A single occurrence generated by expanding a Recurring Transactions Config rule's schedule from its Start Date through today. Expansion is done by a deterministic script, not Claude — see [ADR-0002](./docs/adr/0002-recurring-schedule-expansion-happens-in-a-script.md). Generated occurrences go through the same Needs-Review-free path straight to dedupe (Date + Amount + Notes against the Transaction Log) and are written if not already present — the full history is re-expanded and re-checked every run rather than tracking a separate "last run" cursor.
_Avoid_: Scheduled transaction, generated transaction

**Dashboard**:
The local web app that's the primary interface for viewing budget data and editing the Recurring Transactions Config — replaces Google Sheets as the interface. Runs locally (a small backend plus a browser frontend) against the local database; Transaction data never leaves the machine. Does not handle Needs Review resolution (that stays the terminal prompt flow) or Statement Export processing — those remain scripted, chat-adjacent flows separate from the Dashboard. See [ADR-0008](./docs/adr/0008-dashboard-is-a-local-web-app-not-a-hosted-artifact.md).
_Avoid_: UI, frontend, web app, spreadsheet

**Financial Year**:
The July 1–June 30 window the Dashboard's Overview tab is organised around — its selector shows the twelve months of one Financial Year plus a Full year option, matching the Australian financial year convention already implicit in this project's card issuers (ANZ, NAB).
_Avoid_: FY, Calendar year

**Full year**:
The Overview tab's other selector state, alongside a specific month: aggregates every Transaction in the Financial Year to date, rather than one month. The Dashboard's default view on open. For the current (in-progress) Financial Year, "to date" means elapsed months only, including the current month before it's finished — a month that hasn't happened yet contributes $0, it isn't skipped. See [ADR-0011](./docs/adr/0011-full-year-overview-is-a-selector-state-not-a-tab.md).
_Avoid_: Annual Overview, Year view, Yearly

**Net Balance**:
A Dashboard stat tile: a month's Income total minus that same month's Expense total. Deliberately excludes Transfers — a Transfer neither adds to nor subtracts from Net Balance, since it's money moved, not spent or earned. See [ADR-0009](./docs/adr/0009-overview-tab-scope-follows-the-approved-mockup.md).
_Avoid_: Net income, Surplus, Cash flow

**Category Budget**:
A user-set monthly target Amount for one Expense Category, edited directly with no history kept — there's no per-month or per-Financial-Year variation, just a single standing target compared against that Category's actual spend on the Dashboard's Budgeted vs Actual table. A Category with no Category Budget set is unbudgeted, not budgeted at $0. See [ADR-0009](./docs/adr/0009-overview-tab-scope-follows-the-approved-mockup.md).
_Avoid_: Budget (too vague — always means Category Budget in this project), Target, Limit, Expected (the Dashboard column label for this value, not the concept's name)
