# Changelog

## v0.5.0 — 2026-10-15

- New Goals tab for savings targets. Set a Goal with a target amount and an end date, then fund it with Contributions. Each Goal shows its progress, whether you're on track and how much to save per month, and you can open a Details view with a trajectory chart. A Split savings tool divides one amount across your active Goals, and the Overview shows a tile with your top three. Archived and deleted Goals move to Past goals.
- Settings has a new Your data section. See where your Database lives and when you last made a Backup, download a Backup, move the Database to another folder or switch to one already there (older Databases are upgraded for you, newer ones are refused), and delete all your data and start again.
- Two new colour themes under Appearance: Sage, a light green, and Plum, a dark purple.
- Orchid is redesigned with white cards on a pink page, matching the other light themes, and a hot-pink accent.
- The Dashboard now shows the running Version under its title, with a Version history page listing what changed in each release.
- Fixed a Category's emoji not appearing on the Overview after you set it elsewhere until you reloaded the page.

## v0.4.1 — 2026-10-11

- Updating no longer stops on leftover files, such as a `budget.db` in the project folder, or on the tool's own `uv.lock` file having changed. `update.bat` and `update.command` still refuse to update if you've edited anything else.

## v0.4.0 — 2026-10-11

- New Display Settings tile on the Settings tab. Pick your Display Currency (27 to choose from), the month your Financial Year starts and whether dates read day-first or month-first, and every amount, date and month list follows. Until you save something, the Dashboard behaves as before: Australian dollars, a July year start and day-first dates.
- The Overview now helps you see where you could cut back. Spending over time and Spending by Category include Bills & Subscriptions alongside everyday expenses, and Top merchants replaces Top Expenses, ranking your spending by merchant so lots of small purchases add up.
- Three new Overview cards: an Outflows breakdown showing how your money splits between Expenses, Bills & Subscriptions and Debt; Recurring Charges, listing each recurring merchant with how often it charges and what it costs a year; and Movers, showing which Categories rose or fell most compared with the previous month or your recent average.
- Subscriptions and Insurance & Bills are no longer starting Categories, since Bills & Subscriptions is now the one home for recurring charges.
- The "What's new" list shown by `update.bat` and `update.command` no longer opens in a scrolling view you have to quit.
- The Mac setup guide now tells you to run `bash ~/Downloads/setup.command`, which works on recent macOS versions that no longer offer right-click, Open. Every release now also carries the Installation Pack files, so the guides' download step always has something to download.

## v0.3.0 — 2026-10-06

- Net Balance is now called Available to Save. The Overview adds Unallocated, the part of it you haven't put towards savings, in a new Balance check beside Income Allocation.
- The Budget tab shows Left to Budget, updating as you type, so you can see straight away whether your plan is balanced or over-budgeted before you save.
- Importing a statement now reuses your past choices. A card transaction whose description has only ever been given one Category before takes it automatically, so fewer land in Needs Review, and the AI gets your recent categorisations as examples. The run summary shows how many were matched this way.
- Updating now runs any pending one-off database changes for you, after backing up your database first. It stops with a clear message if something goes wrong.
- You can delete a Category that only has Category Budgets. Those budgets are removed with it, and when a delete is refused the message says exactly what is blocking it.
- The Edit form in the Transactions table now looks like the rest of the app's inputs.

## v0.2.0 — 2026-10-04

- Bills & Subscriptions is a new Type for regular costs such as the gym, phone plan or insurance. It has its own stat tile, Income Allocation segment, Month by month column, bar in the monthly chart and section in Budgeted vs Actual. Net Balance now takes it into account.
- When you set up a Recurring Transactions Config rule, you can enter a total amount instead of a per-payment amount, and it is split across the schedule. A hint under the field shows the result before you save.
- Choosing Bills & Subscriptions when adding a Transaction shows a tip pointing to that split-a-total option.
- The monthly chart on the Overview is now called Cash Flow by Month, and it only shows a Bills & Subscriptions bar once a month has some.

## v0.1.4 — 2026-10-02

- Fixed predefined Categories you had deleted coming back after the Dashboard restarted.

## v0.1.3 — 2026-09-06

- Fixed `update.bat` failing for installs where `budget.db` wasn't being ignored by the project's Git settings.

## v0.1.2 — 2026-08-30

- A Financial Year / Calendar Year switcher on the Overview now also controls the Budget and Transactions tabs, so all three show the same period. It picks up the Financial Year start month, rather than assuming July.
- The Type Transfer is now called Savings, with default Savings and Investments Categories, and Category Budgets can be set for Savings Categories.
- The Budget tab's monthly editor has a Month Actual column beside the budgeted amounts.
- A "Run now" button lets you generate Recurring Transactions on demand instead of waiting.
- The dashboard guide now covers using the Overview before the scripts.
- Fixed Category Management chips showing white in the Orchid theme.

## v0.1.1 — 2026-08-28

- Fixed the Installation Pack's setup scripts quietly creating a second copy of the project when re-run from inside an existing install.
- Setup now configures the AI Budget Suggestion for you when you choose the AI option, so there is no manual `.env` edit. The Budget tab's empty state and the dashboard guide point to the right scripts.
- Refreshed the README: the Dashboard is now presented as the main way to use the tool, and the one-time setup steps come first.

## v0.1.0 — 2026-08-28

- First release. Bank Statement Exports from ANZ, NAB and Beem are cleaned up, categorised automatically and added to your Transaction Log, with anything uncertain flagged for Needs Review. A one-click runner does it all, and your settings live in a per-user `.env` file.
- Recurring Transactions Config lets you define repeating income and bills that are expanded into scheduled Transactions, and you can edit them in the Dashboard.
- The Dashboard's Transactions tab lets you search, filter, sort, page through, add, edit and delete Transactions. You can export a date range to CSV, or import many at once from a generated Excel template with dropdowns, previewing before you confirm.
- The Overview shows stat tiles, Spending by Category, Top 10 expenses, Budgeted vs Actual with a total Diff badge, and month-by-month and Income vs Expenses views, for a single month or the full year.
- Debt is a Type of its own, shown on the Overview and in the budget. Beem Adjustment now counts as an Expense, and Refund is retired.
- The Budget tab lets you set Category Budgets month by month, with history columns, a Full year grid, Total rows, an Auto-populate menu and AI-written Budget Suggestions.
- Category Management lets you add, rename and delete Categories, with emoji, from the Dashboard.
- Choose a colour theme from Settings: Terracotta, Orchid or Midnight.
- The Installation Pack gives guided setup and update scripts for Windows and macOS, downloaded from GitHub Releases.
