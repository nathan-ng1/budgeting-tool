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
The top-level classification of a Transaction: Income, Expense, Bills & Subscriptions, Debt, or Savings — five fixed Types, in that order. Every Category has exactly one fixed Type. Replaces what was previously called "Category" — see [ADR-0006](./docs/adr/0006-simplify-to-three-types-with-a-flat-category-list.md); Bills & Subscriptions, retired there as a grouping, returns as a Type in [ADR-0024](./docs/adr/0024-reintroduce-bills-and-subscriptions-as-a-fifth-type.md).
_Avoid_: Category (retired for this meaning), Group, Real Income (Dashboard tile copy for the Income Type — no distinct concept, just "Income")

**Category**:
The specific budget label for a Transaction — e.g. Groceries, Rental Expense, Salary. Flat: there's no grouping layer between Category and Type (the old Bills & Subscriptions / Expenses / Debt / Savings / Investments split is gone — Bills & Subscriptions now exists only as a Type, see below). Each Category has one fixed Type, never determined per-Transaction:
- **Income**: Salary, Rental
- **Expense**: Groceries, Dining & Takeaway, Transport, Shopping & Retail, Holidays & Travel, Entertainment & Leisure, Health & Medical, Donations & Giving, Rental Expense, Beem Adjustment
- **Debt**: Mortgage Repayment — populated lazily like Rental and Rental Expense above; the first real non-mortgage Debt (e.g. a car or personal loan) adds its own Category rather than one being speculatively predefined. Unlike Bills & Subscriptions and Savings, no further Categories are predefined ahead of a real case.
- **Bills & Subscriptions**: Insurance, Car Registration, Phone Plan, Internet — predefined for every install rather than populated lazily, and unlocked (freely renamed or deleted in Category Management); see [ADR-0024](./docs/adr/0024-reintroduce-bills-and-subscriptions-as-a-fifth-type.md).
- **Savings**: Savings, Investments, Goals — predefined for every install rather than populated lazily, like Bills & Subscriptions; see [ADR-0022](./docs/adr/0022-rename-transfer-to-savings-with-predefined-categories.md). Savings and Investments are unlocked; Goals is a Locked Category, see Goal below and [ADR-0031](./docs/adr/0031-goals-are-a-locked-savings-category-linked-to-transactions.md).

Every categorised Transaction gets exactly one Category, which determines its Type. Replaces what was previously called "Sub-category" — see [ADR-0006](./docs/adr/0006-simplify-to-three-types-with-a-flat-category-list.md).
_Avoid_: Sub-category (retired), Label, tag

**Bills & Subscriptions**:
A Transaction paying a recurring bill or subscription — an insurance premium, car registration, a phone plan, an internet plan — including irregular ones that land annually or quarterly rather than monthly. One of the five Types, alongside Income, Expense, Debt, and Savings. Distinct from an Expense (ordinary day-to-day spending): a committed, recurring cost rather than discretionary consumption. Starts with four predefined, unlocked Categories. Assignable by the categorisation backend and offered in Needs Review, the same as Income, Expense, and Debt. It is the home of every recurring charge: the former Expense Categories Subscriptions and Insurance & Bills are retired, no longer predefined for new installs. See [ADR-0024](./docs/adr/0024-reintroduce-bills-and-subscriptions-as-a-fifth-type.md), which reverses ADR-0006's folding of this name into Expense.
_Avoid_: Bills (on its own), Fixed costs

**Debt**:
A Transaction that services a borrowing you owe to a lender — reducing the outstanding balance of a loan, including any interest bundled into the same repayment (the Statement Export carries no principal/interest split, so the whole repayment is Debt). One of the five Types, alongside Income, Expense, Bills & Subscriptions, and Savings. Distinct from an Expense (money consumed) and from Savings (money moved to an account you own): a Debt repayment converts cash into equity you hold in an asset, but unlike Savings it is non-discretionary and its counterparty is external. Previously folded into Expense — see [ADR-0006](./docs/adr/0006-simplify-to-three-types-with-a-flat-category-list.md) — split back out by [ADR-0012](./docs/adr/0012-split-debt-back-out-of-expense.md).
_Avoid_: Liability, Loan repayment

**Savings**:
A Transaction that moves money to an account you own and control (a savings or investment account) rather than to a third party. Looks identical to an Expense in a bank export — a debit leaving the account — but is economically distinct: not consumption. One of the five Types, alongside Income, Expense, Bills & Subscriptions, and Debt. Its Category list starts predefined with three: Savings and Investments — the Savings Category shares its name with the Savings Type, a deliberate overlap rather than a naming mistake — and the Locked Category Goals. Predefined rather than lazily populated, since (unlike Debt, which varies person to person) every user has some form of savings or investment account. Never assigned by the categorisation backend or offered in Needs Review: a Savings Transaction is always entered by hand, via the Dashboard's Transactions tab or Recurring Transactions Config, never from a Statement Export — except that a Goals Transaction is entered from the Goals tab or the Transactions tab and never from Recurring Transactions Config. See [ADR-0022](./docs/adr/0022-rename-transfer-to-savings-with-predefined-categories.md), which renames this Type from Transfer and supersedes ADR-0006's lazy-population policy for it.
_Avoid_: Transfer (this Type's retired name — see ADR-0022)

**Locked Category**:
A predefined Category that can't be renamed, deleted or have its emoji changed in Category Management, is never assigned by the categorisation backend or History Match, and is refused on Import. Being locked does not hide a Category from the Transactions form or the Budget editor. Two exist: Beem Adjustment, whose Category is forced by payment direction, and Goals, whose Transactions each belong to a Goal.
_Avoid_: Protected Category, System Category

**Goal**:
A savings target the user sets and tracks on the Goals tab: a title (unique across all Goals, including Past goals, ignoring case and surrounding spaces), an optional description, a target amount, a start date (defaults to today; may be past or future) and a required end date. Not tied to the Financial Year. A Goal's saved amount is the sum of its Contributions whatever their dates, and may exceed the target. Its Status is one of Upcoming (today is before the start date), Active, Achieved (saved has reached the target) or Ended (the end date has passed with the target unmet). An Active Goal is On track when saved is at or above its pace — the target spread evenly from start to end date — and Behind otherwise. Its required amount per month is what is still to save divided by the calendar months left (elapsed calendar months from today to the end date, a partial month rounded up, minimum one), shown beside an Original plan hint: the target divided by the calendar months from start to end, counted the same way. A Goal can be archived or deleted, which moves it to Past goals; neither touches its Contributions. See [ADR-0031](./docs/adr/0031-goals-are-a-locked-savings-category-linked-to-transactions.md).
_Avoid_: Target (on its own — also used for a Category Budget), Pot, Envelope

**Contribution**:
A Savings Transaction in the Locked Category Goals that funds one Goal. An ordinary Transaction in every other respect, so it counts toward Saved, Available to Save and Unallocated exactly like any other Savings Transaction. Created from the Goals tab (Add contribution, or Split savings) or from the Transactions tab by choosing the Goals Category and a Goal; an existing Savings or Investments row can be turned into one by editing it. Always positive: money is never withdrawn from a Goal.
_Avoid_: Deposit, Allocation, Goal Transaction

**Past goals**:
The collapsed list on the Goals tab of Goals that were archived or deleted, each with an Archived or Deleted badge. Deleting is soft, there is no permanent delete, and any Past goal can be reactivated, which opens its pre-filled edit form so extending the end date is one step. An Ended Goal is not a Past goal: it stays in the main list until the user archives or deletes it.
_Avoid_: Completed goals, Inactive goals, Trash

**Goals tab**:
The Dashboard tab (alongside Overview, Transactions, Budget, Settings) for creating and tracking Goals. It shows no Financial Year/Calendar Year switcher. Each Goal appears as a card with its Status, progress and pace, required amount per month, and Add contribution, Edit, Archive and Delete actions, plus a read-only Details view with a trajectory chart and its Contributions. A Split savings tool divides one total across active Goals by percentage, writing one Contribution per Goal and putting any remainder in Savings or Investments. The Overview tab carries a tile of the top three active Goals.
_Avoid_: Goals page, Savings goals tab

**Outflows**:
Expense + Bills & Subscriptions + Debt for the period shown: every dollar that left as a cost or a repayment. Never includes Savings, which is money moved to an account you own. The superset behind the Dashboard's Outflows breakdown; Spending (below) is the part of it without Debt.
_Avoid_: Cash outflows, Cash flow (Available to Save's retired alias), Spend (ambiguous between Outflows and Spending)

**Spending**:
Expense + Bills & Subscriptions for the period shown: Outflows without Debt, the costs a household can realistically change. Debt is kept out because it is non-discretionary and already has its own card. Within Spending, Bills & Subscriptions is the *committed* part (recurring, agreed in advance) and Expense the *discretionary* part (day-to-day consumption). "Committed" and "discretionary" are glossary-only reasoning aids — the Dashboard labels these by Type name and never uses either word.
_Avoid_: Expenses (that's the Expense Type alone), Outflows (that includes Debt)

**Transactions Inbox**:
The external folder (path set via `TRANSACTIONS_INBOX` in `.env`) where unsanitised Statement Exports are saved directly from a card issuer's site. Claude never reads this location — only the Sanitising script does.
_Avoid_: Raw folder, landing directory, local directory

**Transaction Log**:
The database table this process writes to. One row per categorised Transaction: Date, Amount (always positive, two decimal places, regardless of the Statement Export's sign — except Category Beem Adjustment, a deliberate, narrow exception stored negative so it reduces Expense totals, see [ADR-0015](./docs/adr/0015-beem-adjustment-reduces-expense-instead-of-income.md)), Type, Category, Notes (the merchant description carried over from the Statement Export), and — only for a Contribution — the Goal it funds. Before writing, each Transaction is checked against existing Transaction Log rows (matching Date + Amount + Notes) and skipped if already present, since Statement Export date ranges can overlap between runs. A row can also be added directly (not just via Statement Export or Recurring Transaction expansion) through the Dashboard's Transactions tab, which offers full add/edit/delete over the Transaction Log; such a row is checked against the same Date + Amount + Notes dedupe as any other on the next Statement Export run. Previously a Google Sheets tab — the Sheet is retired as the live store, see [ADR-0005](./docs/adr/0005-migrate-transaction-log-and-recurring-config-to-a-local-database.md).
_Avoid_: Budget sheet, spreadsheet, Google Sheet, Description (for the Notes field — Notes is the term everywhere it appears, including the Dashboard's Transactions tab)

**Database**:
The single local file holding everything the Dashboard shows: the Transaction Log, the Recurring Transactions Config, Category Budgets, Categories, Goals, the Budget Suggestion and Display Settings. Where it lives is chosen in Settings, and Settings also shows that location. It is found through a `DATABASE_PATH` override if one is set, then a pointer file, then the default per-user data folder. See [ADR-0030](./docs/adr/0030-database-location-is-chosen-in-settings-stored-in-env-and-switched-live.md) and [ADR-0032](./docs/adr/0032-one-data-location-resolver-with-a-pointer-file.md).
_Avoid_: Data file, save file, the data (on its own)

**Backup**:
A downloaded point-in-time copy of the Database, kept wherever the user chooses. Settings shows when one was last made. It is a complete Database in its own right, so it can later be used as the Dashboard's Database.
_Avoid_: Export (reserved for the Transactions tab's CSV), Snapshot, Dump

**Needs Review**:
The checkpoint where the configured categorisation backend flags every Transaction (other than a History Match, which never reaches the backend) it can't confidently assign a Category to (a `needs_review` flag in its structured response), and `uv run python -m statement_export` prompts you for each one right in the terminal. Nothing is written to the Transaction Log until every Needs Review item for that file is resolved.
_Avoid_: Uncategorised, low-confidence

**History Match**:
A card Statement Export Transaction whose Type and Category are taken straight from earlier Transaction Log rows with the same Notes — compared ignoring case, digits, and spacing, so the same merchant under a different store number still counts — instead of from the categorisation backend. A History Match is never sent to the backend and never goes to Needs Review. It only happens when every earlier row with those Notes agrees on one Category; if they've ever disagreed (e.g. a merchant you later moved to a different Category), the Transaction goes to the backend as normal. Beem Reports never produce History Matches — a Beem message is free text too vague to match on. A History Match never assigns a Savings Category either, since Savings is manual-entry only. The Transaction Log is the only source: there's no separate list of rules, so editing a row on the Dashboard changes what future Transactions match to. Beem Adjustment rows are never matched against, since their Category is forced by direction rather than chosen. Those same past rows are also given to the backend as examples for the Transactions that aren't History Matches, including outgoing Beem rows, but there they're only a hint. See [ADR-0026](./docs/adr/0026-history-matches-skip-the-categorisation-backend.md).
_Avoid_: Known Merchant, Remembered Category, rule, auto-categorisation

**Processed archive**:
`.data\processed\` — where a Statement Export moves once its Transactions have been successfully written to the Transaction Log. Anything still sitting directly in `.data\` is outstanding and hasn't been processed yet.
_Avoid_: Archive, done folder

**Recurring Transactions Config**:
A database table — one row per predictable, known-in-advance recurring item (salary, mortgage payments, etc.), independent of any Statement Export. Columns: Amount, Type, Category, Notes, Frequency (Weekly/Monthly), Interval (every N periods), Day (day-of-week for Weekly, day-of-month for Monthly — clamped to the last day of the month if it doesn't exist, e.g. Day=31 in February), Start Date, End Date (optional — blank means recurs indefinitely). Editable via the Dashboard. When adding or editing a rule, the Dashboard also lets a user enter a Total Amount instead of the per-occurrence Amount, for any Type/Category: the Total is divided by the number of occurrences the rule's own schedule expands to between Start Date and End Date (End Date is required for this), rounded to the nearest cent — any cumulative drift from the Total is accepted rather than corrected. This is only a way of entering the Amount: the saved rule is an ordinary rule, nothing about the split is stored, and later edits work on its Amount directly. Previously `config\recurring-transactions.xlsx`, hand-edited outside Claude — retired, see [ADR-0005](./docs/adr/0005-migrate-transaction-log-and-recurring-config-to-a-local-database.md).
_Avoid_: Recurring config, schedule file, .xlsx

**Recurring Transaction**:
A single occurrence generated by expanding a Recurring Transactions Config rule's schedule from its Start Date through today. Expansion is done by a deterministic script, not Claude — see [ADR-0002](./docs/adr/0002-recurring-schedule-expansion-happens-in-a-script.md). Generated occurrences go through the same Needs-Review-free path straight to dedupe (Date + Amount + Notes against the Transaction Log) and are written if not already present — the full history is re-expanded and re-checked every run rather than tracking a separate "last run" cursor. Triggered one of two ways, both expanding through the same target date (today) and sharing identical dedupe: automatically as part of `process_statement_export` (a Statement Export run always expands every rule too, not just the file's own rows), or manually via the "Run now" button on the Dashboard's Recurring Transactions Config screen — for a user without a Statement Export pipeline to run (see [ADR-0018](./docs/adr/0018-non-ai-path-is-dashboard-only.md)), but available unconditionally to any user, since the Dashboard has no runtime concept of an AI-enabled install.
_Avoid_: Scheduled transaction, generated transaction

**Dashboard**:
The local web app that's the primary interface for viewing budget data and editing the Recurring Transactions Config — replaces Google Sheets as the interface. Runs locally (a small backend plus a browser frontend) against the local database; Transaction data never leaves the machine. Does not handle Needs Review resolution (that stays the terminal prompt flow) or Statement Export processing — those remain scripted, chat-adjacent flows separate from the Dashboard. See [ADR-0008](./docs/adr/0008-dashboard-is-a-local-web-app-not-a-hosted-artifact.md).
_Avoid_: UI, frontend, web app, spreadsheet

**Version**:
The number of a tagged release of the tool (e.g. `0.4.1`), shown on the Dashboard as `v0.4.1` directly under its title. It changes only when a release is cut, so unreleased commits still report the last released Version. Shown in both the Collaborator Edition and the Retail Edition.
_Avoid_: Build number, Release (that's the GitHub object that carries the Installation Pack)

**Version History**:
The Dashboard page, linked from the top right of its header, listing every Version newest-first with its release date and a short plain-language summary of what changed. Distinct from GitHub's auto-generated release notes, which list raw PR titles and are not shown in the Dashboard. Both editions have one, but the content and how it ships with a release differ by edition.
_Avoid_: Changelog (that's the Collaborator Edition's source file, not the page), Release notes

**Financial Year**:
The twelve-month window the Dashboard's Overview, Budget, and Transactions tabs can be organised around — the default framing, and one of the two options on the Financial Year/Calendar Year switcher shared across those three tabs (see [ADR-0021](./docs/adr/0021-financial-year-switcher-and-calendar-year-toggle.md)). It begins on the first day of a month the user chooses in Settings, defaulting to July (the Australian convention, implicit in this project's card issuers ANZ and NAB, giving July 1–June 30); a start on any other day of the month, such as the UK's 6 April, is not supported. Its selector shows the twelve months of one Financial Year plus a Full year option.
_Avoid_: FY

**Calendar Year**:
The January 1–December 31 window — the switcher's other framing, alongside Financial Year (see [ADR-0021](./docs/adr/0021-financial-year-switcher-and-calendar-year-toggle.md)). Reorders the twelve month pills to run Jan→Dec and changes what "Full year" aggregates, but doesn't change how any individual month's figures are computed. When the Financial Year is configured to start in January the two framings are identical, so the switcher is hidden.
_Avoid_: CY

**Display Currency**:
The single currency the Dashboard shows every amount in, chosen in Settings from a single list of currencies, each carrying its own predefined conventions (symbol and its position, thousands and decimal separators) — the number format is not a separate choice. One per install, display only: no exchange rates, no conversion, and no Transaction carries a currency of its own. Changing it relabels existing amounts rather than converting them. Limited to currencies with 0 or 2 decimal places; the few with 3 (e.g. Kuwaiti dinar) are not offered, since every amount is held to two decimals. Defaults to the Australian dollar.
_Avoid_: Currency (on its own — implies per-Transaction currency), Locale (the format rules are part of the Display Currency, not a separate choice)

**Date Order**:
Whether the Dashboard writes a date day-first ("19 Aug") or month-first ("Aug 19"), chosen in Settings. Month names are always English, since the Dashboard is English-only. There is no week-start-day setting: a Weekly Recurring Transactions Config rule stores a day of the week, which doesn't depend on which day a week begins.
_Avoid_: Date format (implies a full format picker, which isn't offered), Locale

**Full year**:
The Overview tab's other selector state, alongside a specific month: aggregates every Transaction in the active Financial Year or Calendar Year to date, rather than one month. The Dashboard's default view on open. For the current, in-progress year, "to date" means elapsed months only, including the current month before it's finished — a month that hasn't happened yet contributes $0, it isn't skipped. See [ADR-0011](./docs/adr/0011-full-year-overview-is-a-selector-state-not-a-tab.md). The Budget tab reuses the same pill and label for its own, differently-scoped Full year state — see Budget tab, below.
_Avoid_: Annual Overview, Year view, Yearly

**Available to Save**:
`Income − Expenses − Debt − Bills & Subscriptions` for the period shown: what Income left after everything consumed or owed, and so the most that could have gone to Savings. Money moved to Savings is never subtracted — a Savings Transaction is money moved to an account you still own, not spent. Answers "how much could I save?"; its counterpart Unallocated answers "did every dollar get a job?". Formerly named Net Balance, renamed because users who budget every dollar (Savings included) read it as their should-be-$0 balance. See [ADR-0009](./docs/adr/0009-overview-tab-scope-follows-the-approved-mockup.md), [ADR-0012](./docs/adr/0012-split-debt-back-out-of-expense.md) (added `− Debt`), [ADR-0024](./docs/adr/0024-reintroduce-bills-and-subscriptions-as-a-fifth-type.md) (added `− Bills & Subscriptions`), and [ADR-0022](./docs/adr/0022-rename-transfer-to-savings-with-predefined-categories.md) (renamed Transfer to Savings).
_Avoid_: Net Balance (this figure's retired name), Net income, Surplus, Cash flow

**Unallocated**:
`Income − Expenses − Bills & Subscriptions − Debt − Savings` for the period shown: Income that wasn't spent, paid, or moved to Savings. Always equals Available to Save minus what was saved. $0 is the target for anyone who budgets every dollar; a negative figure means outflows ran past Income.
_Avoid_: Remaining (the income-allocation bar's former label for this figure), Left over, Net Balance

**Left to Budget**:
Unallocated's planned counterpart for one month: budgeted Income minus the Category Budgets of every Expense, Bills & Subscriptions, Debt, and Savings Category. An unbudgeted Category adds nothing. $0 means every budgeted dollar of Income has a job. Kept distinct from Unallocated because plan and actuals diverge — Left to Budget can be $0 while Unallocated comes in negative.
_Avoid_: Unallocated (that's actuals), Unbudgeted (means a Category with no Category Budget), Remaining

**Category Budget**:
A user-set target Amount for one Category in one specific month — every month stands alone, edited and kept independently of every other month, with no averaging or carry-forward between them. Applies to any Category, across every Type — Income, Expense, Bills & Subscriptions, Debt, and Savings. A Category with no Category Budget set for a given month is unbudgeted for that month, not budgeted at $0. A Category Budget never keeps its Category alive: deleting a Category removes every Category Budget it has, across all months; only a Transaction or a Recurring Transactions Config rule in that Category prevents the delete. Compared against that Category's actual for the same month on the Dashboard's Budgeted vs Actual table, which partitions its rows by Type; a Savings Category coming in above its Budgeted Amount reads as favourable, the same direction as Income, not as overspend. See [ADR-0009](./docs/adr/0009-overview-tab-scope-follows-the-approved-mockup.md) (introduced the concept, originally Expense-only and month-invariant), [ADR-0013](./docs/adr/0013-category-budget-is-per-month-across-income-expense-and-debt.md) (made it per-month and extended it to Income/Debt), [ADR-0023](./docs/adr/0023-extend-category-budget-to-savings-categories.md) (extended it to Savings), and [ADR-0024](./docs/adr/0024-reintroduce-bills-and-subscriptions-as-a-fifth-type.md) (budgetable from the start for Bills & Subscriptions).
_Avoid_: Budget (too vague — always means Category Budget in this project), Target, Limit, Expected (the Dashboard's original column label for this value, retired in favour of Budgeted once the label and the concept's name matched)

**Budget tab**:
The Dashboard tab (alongside Overview, Transactions, Goals, Settings) for setting Category Budgets one Financial Year month at a time and reviewing the current Budget Suggestion. Picks up the shared Financial Year/Calendar Year switcher (Overview's since [ADR-0021](./docs/adr/0021-financial-year-switcher-and-calendar-year-toggle.md)) in a later ticket. Its month selector also offers a Full year pill showing a read-only 12-month × Category grid of everything budgeted across the active year — unlike the Overview tab's Full year, this grid is never restricted to elapsed months (a Category Budget set ahead for a future month still shows), since it is summarising budgets set, not aggregating actual Transactions to date. Selecting it offers no editing surface at all; editing only happens through an individual month pill. Both the per-month editor and the Full year grid show a Total row per Type, summing that Type's Budgeted Amount across its Categories (live, before Save, in the per-month editor). The per-month editor also offers an Auto-populate control next to Save budgets, wholesale-overwriting every Category's Budgeted Amount field (staged, not yet saved) from either last month's actuals or last month's own Category Budgets, mirrored exactly Category-by-Category — see Issue #77. Named as a later-phase placeholder as far back as [ADR-0008](./docs/adr/0008-dashboard-is-a-local-web-app-not-a-hosted-artifact.md) and left unwired through [ADR-0009](./docs/adr/0009-overview-tab-scope-follows-the-approved-mockup.md); built out by [ADR-0013](./docs/adr/0013-category-budget-is-per-month-across-income-expense-and-debt.md) (per-month editor), Issue #64 (read-only Full year grid), and Issue #77 (Auto-populate, Type Total rows).
_Avoid_: Budget screen, Budgeting tab

**Installation Pack**:
The `setup`/`update`/setup-guide bundle that takes a new user from nothing installed to a running Dashboard (and, if they hold an AI subscription, the Statement Export pipeline too) — `windows/setup.bat` + `windows/update.bat` + `docs/setup-guide.html` on Windows, `mac/setup.command` + `mac/update.command` + `docs/setup-guide-mac.html` on macOS (issue #117), both wrapping the same `src/setup` logic. `setup.bat`/`setup.command` is a standalone bootstrapper — runnable before Git or a clone exist — distributed as a GitHub Release asset; it branches on whether the user holds an AI subscription, since automated categorisation has no manual/null backend and so cannot be made to work without one. See [ADR-0017](./docs/adr/0017-installation-pack-is-a-bootstrapper-distributed-via-releases.md), [ADR-0018](./docs/adr/0018-non-ai-path-is-dashboard-only.md), [ADR-0019](./docs/adr/0019-update-checks-are-automatic-updates-are-manual.md).
_Avoid_: Installer, setup script (for the pack as a whole — `setup.bat`/`setup.command` is fine for the script itself)

**Collaborator**:
Someone given access to the private repo who runs the Collaborator Edition, installed and updated via the Installation Pack.
_Avoid_: User (ambiguous between Collaborator and Buyer), developer

**Buyer**:
A member of the public who purchased the Retail Edition (sold via Etsy). Never has repo access or sees source.
_Avoid_: Customer, user, client

**Collaborator Edition**:
The full tool — Dashboard plus the Statement Export pipeline and other AI-backed flows — run from a clone of the repo.
_Avoid_: Dev build, full version

**Retail Edition**:
The compiled, Dashboard-only build of the tool sold to Buyers; contains none of the Statement Export pipeline or AI-backed flows.
_Avoid_: Paid version, public version, packaged app

**Budget Suggestion**:
A written analysis of how actual spend has tracked against Category Budgets recently, covering Expense and Debt Categories only (Income is excluded — under/over-earning isn't the kind of thing this advises on). One standing write-up at a time, not tied to any particular month: regenerating it replaces the previous write-up outright, no history kept. Produced by a scripted, deliberately non-interactive flow — the same shape as Categorising a Transaction (see [ADR-0004](./docs/adr/0004-categorisation-backend-is-pluggable-and-scripted.md)), not something triggered live from the Dashboard. See [ADR-0014](./docs/adr/0014-budget-suggestion-is-a-scripted-flow-not-a-live-dashboard-call.md).
_Avoid_: Budget advice, AI insights, Recommendation
