# Category Budget is per-(Category, month), across Income/Expense/Debt, not a flat Expense-only value

ADR-0009 introduced Category Budget as a single standing target Amount per Expense Category, with
"no per-month or per-Financial-Year variation" by design — a deliberate simplification to unblock
the first Budgeted vs Actual table. A `/grill-with-docs` session scoping the Budget tab (previously
just an unwired nav label) revisited that simplification: a flat target can't express "I budget more
for Holidays & Travel in December than in March," which is the actual point of a Budget tab. Category
Budget now varies independently per (Category, year, month) — `category_budgets` gains `year`/`month`
into its key alongside `category` — and extends to Income and Debt Categories, not just Expense,
since the Budget tab is meant to cover all three budgetable Types.

This resolves ADR-0011's placeholder: the annual Overview's Budgeted vs Actual columns were always
"—" because a flat, non-monthly Category Budget couldn't be multiplied into a real annual figure
without fabricating one. With a genuine per-month value, a Category's annual Budgeted figure is now
the sum of its per-month budgets across the Financial Year's elapsed months — a month with no budget
set contributes $0 to that sum rather than making the whole Category read as unbudgeted for the year,
consistent with "unset ≠ $0" applying at the per-month grain, not the per-Category-year grain.

An evergreen per-calendar-month value (one "December" budget reused every year, no year component)
was considered and rejected: it's less data entry, but can't express "this December differs from last
December," which per-(year, month) can.

## Consequences

- Every existing Category Budget row is Expense-only and month-invariant under the old schema; there
  is no data to migrate (the table is empty at the time of this decision) — the schema change ships
  as a clean replacement, not a migration.
- ADR-0011's "annual Expected/Diff/% columns are always —" rule no longer applies; its own text
  flagged this as a placeholder pending "a real per-month-capable Category Budget," which this ADR is.
