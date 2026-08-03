# Budgeting Tool

A personal, manually-triggered process that turns credit card statement exports into categorised entries in a Google Sheets budget.

## Language

**Statement Export**:
A raw CSV file downloaded from a card issuer's online banking and dropped into `.data/`, named `{Issuer}_{yyyymmdd}.csv` (e.g. `ANZ_20260730.csv`). Contains one row per Transaction, no header row.
_Avoid_: Raw CSV, transaction file

**Transaction**:
A single row within a Statement Export: a date, a signed amount (negative = spend, positive = payment/credit), and a merchant description.
_Avoid_: Line, entry, record

**Beem Report**:
A CSV export from the Beem P2P payment app, dropped into `.data/` following the same `{Issuer}_{yyyymmdd}.csv` naming convention as a Statement Export (e.g. `Beem_20260730.csv`). Distinct from a Statement Export: it has a header row, each row's sign is bidirectional — derived from whether the user was Payer or Recipient, not a fixed sign-per-column convention — and it is Income-eligible: an incoming Beem Transaction is written to the Transaction Log as Income, not dropped the way a Payments & Refunds credit is.
_Avoid_: Beem export, Beem statement

**Payments & Refunds**:
Any Transaction with a positive Amount (a credit to the card — a bill payment or a refund). Dropped from processing entirely: never categorised, never written to the Transaction Log. This is a plain sign check with no netting or refund-matching logic — a spend Transaction that was later refunded is still categorised and logged as spending; only its matching positive-Amount credit is dropped.
_Avoid_: Credit, income

**Sanitising**:
An issuer-specific step that strips personal information from a Statement Export before it's processed further. Runs as a Python script, never as something Claude does directly — see [ADR-0001](./docs/adr/0001-sanitising-happens-outside-claudes-read-access.md). For ANZ, sanitising is a no-op: ANZ exports contain no personal identifiers (no name, account number, or card number).
_Avoid_: Cleaning, scrubbing

**Category**:
The top-level budget grouping in the Google Sheet: Income, Expenses, Bills & Subscriptions, Savings, Debt, Investments. Credit card Transactions (from a Statement Export) only ever land in **Expenses** or **Bills & Subscriptions**; the other four Categories are populated exclusively by Recurring Transactions, not Statement Export processing — except Income, which incoming Beem Report Transactions also populate, via the Beem Adjustment Sub-category.
_Avoid_: Type, group

**Sub-category**:
The finer-grained budget label under a Category. Each Sub-category has one fixed Category — never determined per-Transaction:
- **Bills & Subscriptions**: Donations & Giving, Subscriptions, Insurance & Bills
- **Expenses**: Groceries, Dining & Takeaway, Transport, Shopping & Retail, Holidays & Travel, Entertainment & Leisure, Health & Medical
- **Income**: Salary, Rental, Beem Adjustment
- **Debt**: Mortgage Repayment

Every categorised Transaction gets exactly one Sub-category, which determines its Category. Sub-categories for Income/Debt/Savings/Investments only need to exist for what's actually configured in the Recurring Transactions Config or, for Income, in Beem Report processing — built from real cases, not speculatively.

**Subscriptions** (sub-category) means the Transaction *itself* is a recurring charge (same merchant, regular cadence — e.g. the Anthropic Claude charge), not "sold by a platform that also offers subscriptions." A one-off purchase from a subscription-style platform (e.g. a single Steam game purchase) goes by what was bought, landing in Entertainment & Leisure instead.
_Avoid_: Label, tag, Bill (a Bill is a Transaction whose Sub-category maps to Bills & Subscriptions, not a category name itself)

**Transactions Inbox**:
The external folder (`D:\natha\Documents\Transactions`) where unsanitised Statement Exports are saved directly from a card issuer's site. Claude never reads this location — only the Sanitising script does.
_Avoid_: Raw folder, landing directory, local directory

**Transaction Log**:
The Google Sheet tab this process writes to. Six columns are filled per categorised Transaction — Month, Day, Amount, Category, Sub-Category, Notes (spreadsheet columns C, D, G, J, L, M) — Notes holds the merchant description carried over from the Statement Export, and Amount is always written positive, to two decimal places, regardless of the Statement Export's sign. Other columns (e.g. Full date) are formula-derived and never written directly. Month, Amount, Category and Sub-Category each sit one cell to the right of a wide merged header label (e.g. the "Category" label lives in I, the value goes in J; K is a blank spacer, not the Sub-Category column) — but Notes' header isn't merged, so its value sits directly in M, not one column further right; N is unused. See `docs/agents/google-sheets-mcp.md` for the full verified layout. Before writing, each Transaction is checked against existing Transaction Log rows (matching Full date + Amount + Notes) and skipped if already present, since Statement Export date ranges can overlap between runs.
_Avoid_: Budget sheet, spreadsheet

**Needs Review**:
The checkpoint where Claude lists every Transaction it can't confidently assign a Sub-category to, inline in the chat, and waits for you to assign one. Nothing is written to the Transaction Log until every Needs Review item is resolved.
_Avoid_: Uncategorised, low-confidence

**Processed archive**:
`.data\processed\` — where a Statement Export moves once its Transactions have been successfully written to the Transaction Log. Anything still sitting directly in `.data\` is outstanding and hasn't been processed yet.
_Avoid_: Archive, done folder

**Recurring Transactions Config**:
`config\recurring-transactions.xlsx` — one row per predictable, known-in-advance recurring item (salary, rental income, mortgage payments, etc.), independent of any Statement Export. Columns: Amount, Category, Sub-Category, Notes, Frequency (Weekly/Monthly), Interval (every N periods), Day (day-of-week for Weekly, day-of-month for Monthly — clamped to the last day of the month if it doesn't exist, e.g. Day=31 in February), Start Date, End Date (optional — blank means recurs indefinitely).
_Avoid_: Recurring config, schedule file

**Recurring Transaction**:
A single occurrence generated by expanding a Recurring Transactions Config rule's schedule from its Start Date through today. Expansion is done by a deterministic script, not Claude — see [ADR-0002](./docs/adr/0002-recurring-schedule-expansion-happens-in-a-script.md). Generated occurrences go through the same Needs-Review-free path straight to dedupe (Full date + Amount + Notes against the Transaction Log) and are written if not already present — the full history is re-expanded and re-checked every run rather than tracking a separate "last run" cursor.
_Avoid_: Scheduled transaction, generated transaction
