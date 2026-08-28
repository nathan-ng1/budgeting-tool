# The Full year Overview is a selector-pill state inside Overview, not a separate tab

ADR-0009 flagged "the annual Overview (no month selected)" as a separate, not-yet-designed screen.
A completed mockup (`docs/mockups/Annual Overview.html`, scoped during a `/grill-with-docs` session)
resolves that: Full year is a 13th pill in the same month selector the per-month Overview already
uses, not a new tab — the Overview tab renders per-month or full-year sections depending on which
pill is active, and Full year is now the Dashboard's default view on every load.

This introduces one behavioural rule that isn't obvious from the code: for the current
(in-progress) Financial Year, Full year totals only **elapsed months**, including the current month
before it's finished. The "Month by month" table and "Income vs Expenses by month" chart still show
all 12 months of the Financial Year, but months that haven't happened yet render as $0/empty rows
rather than being omitted. Stat tiles and monthly averages divide by elapsed months, not 12.

The annual Budgeted vs Actual table's Expected/Diff/% columns are always "—", for every Category,
regardless of whether a Category Budget is set. A Category Budget is currently a single flat monthly
amount (CONTEXT.md) with no per-month variation; multiplying that by elapsed months would produce a
number that looks like a real annual target without being one. Real annual budgeting (a
per-month-capable Category Budget) is deferred to a future feature - only the Actual column is real
for Full year today.

Full year gets its own endpoint, `GET /api/annual-overview?year=X`, rather than an optional `month`
on `/api/overview` — the response shapes differ enough (a month-by-month breakdown, a 12-month
chart) that a shared endpoint would mean every caller branching on which fields are present.

## Consequences

- Full year, like per-month Overview, has no Financial Year switcher — it always shows the FY
  containing today. Viewing a past Financial Year's Full year stays out of scope until a switcher
  exists. **Resolved by [ADR-0021](./0021-financial-year-switcher-and-calendar-year-toggle.md)**.
- When a real per-month-capable Category Budget is built, the annual Expected/Diff/% columns need
  revisiting — this ADR's "always —" rule is a placeholder, not a permanent design. **Resolved by
  [ADR-0013](./0013-category-budget-is-per-month-across-income-expense-and-debt.md)**: Category Budget
  is now per-month, so the annual figure is a real sum over elapsed months, not a placeholder "—".
- `/api/annual-overview` and `/api/overview` will diverge over time as separate contracts; a future
  reader comparing them should not expect them to converge.
