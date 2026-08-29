# Extend Category Budget to Savings Categories

[ADR-0013](./0013-category-budget-is-per-month-across-income-expense-and-debt.md) extended Category
Budget from Expense-only to Income/Expense/Debt, but never argued Savings *shouldn't* be budgetable —
it simply wasn't in scope yet, since Savings (then Transfer) had no predefined Categories to budget
against at the time. [ADR-0022](./0022-rename-transfer-to-savings-with-predefined-categories.md) gave
Savings its own predefined Categories (Savings, Investments), but left the exclusion in place, so a
user who wants to set a monthly savings target and see how actual Savings tracked against it has had
no way to do so anywhere in the Dashboard.

This widens Category Budget to cover Savings Categories too, everywhere it already appears: the Budget
tab's per-month editor and Full year grid, and the Overview tab's Budgeted vs Actual card (both
per-month and annual views). The three independent places that hardcoded "budgetable Types =
Income/Expense/Debt" — `dashboard.queries.BUDGETABLE_TYPES`, `dashboard.budgets.BUDGETABLE_TYPES`, and
the frontend `BudgetedVsActual.jsx`'s `SECTIONS` list — are all widened together, so Savings budgeting
doesn't half-appear. No change is needed to the actual/budget aggregation or storage layers: the
per-category actual aggregator, the `category_budgets` table, and Savings' signed-amount convention
were already Type-agnostic.

Saving more than budgeted reads as favourable, not as overspend — the same direction Income already
gets, flipped from Expense/Debt's "over is adverse" reading. Budget Suggestion (the scripted AI
write-up) is deliberately **not** extended to Savings: it keeps analysing Expense and Debt Categories
only, unchanged, since this ADR is about what a user can budget against, not about what the write-up
comments on.

## Consequences

- Supersedes ADR-0013's Income/Expense/Debt framing of which Types Category Budget applies to, and
  CONTEXT.md's "Savings has none to budget" line. The per-(Category, month) shape ADR-0013 introduced
  is unchanged — only the set of budgetable Types grows.
- `dashboard.budgets.BUDGETABLE_TYPES` (the wire-shape grouping constant) simplifies to reuse
  `transaction_log.categories.TYPE_ORDER` directly, since it no longer excludes anything.
- Savings sits last in both the Budget tab and the Overview card's Budgeted vs Actual table, matching
  the existing canonical `TYPE_ORDER = (Income, Expense, Debt, Savings)` — no new ordering logic.
- Net Balance's formula (`Income − Expenses − Debt`) is unaffected — Savings still isn't subtracted,
  unchanged from ADR-0022. This ADR is about budgeting *against* Savings Categories, not about how
  Savings counts toward other Overview figures.
- `budget_suggestions.run.generate_budget_suggestion`'s row filter, previously just `type != "Income"`,
  now also excludes Savings explicitly — the wider `BUDGETABLE_TYPES` it draws rows from would
  otherwise leak Savings into the write-up's analysis.
