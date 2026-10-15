# Spending includes Bills & Subscriptions; the overlapping Expense Categories are retired

[ADR-0012](./0012-split-debt-back-out-of-expense.md) kept Spending by Category, Top Expenses, and
Expenses over time Expense-only, and [ADR-0024](./0024-reintroduce-bills-and-subscriptions-as-a-fifth-type.md)
left the Expense Categories Subscriptions and Insurance & Bills overlapping the new Bills &
Subscriptions Type "for now". That left every Bills & Subscriptions charge invisible to the views
that answer "where does my money go?". This decides both: the Dashboard's category- and
merchant-level views cover **Spending** (Expense + Bills & Subscriptions, see `GLOSSARY.md`), and
Subscriptions and Insurance & Bills are retired so Bills & Subscriptions is the single home of
recurring charges.

Debt stays outside Spending and keeps its own card: it is non-discretionary, and in a ranked list it
would always sit at the top and bury everything the user can change. **Outflows** (Spending + Debt)
is used only where the full picture is wanted — the Outflows breakdown chart.

## Consequences

- Expenses over time becomes **Spending over time** (Expense + Bills & Subscriptions, one cumulative
  line), Spending by Category gains Bills & Subscriptions Categories, and Top Expenses is replaced by
  Top merchants (Spending grouped by merchant, by normalised Notes, ranked by total; Debt and Beem
  Adjustment excluded). All three previously Expense-only views in ADR-0012 are superseded.
- Movers, the new single-month comparison of Categories against a prior period, covers Spending
  Categories only: Debt stays out of ranked lists here too, so a repayment doesn't dominate the bars.
- The Dashboard labels Types by name only. "Committed" and "discretionary" are glossary-only
  reasoning aids, never Dashboard copy, so users aren't asked to learn a second vocabulary.
- Subscriptions and Insurance & Bills stop being seeded for new installs. No migration is shipped:
  existing installs keep any rows and rules in them as ordinary, deletable Expense Categories, which
  Recurring Charges (Bills & Subscriptions only) won't show until they are moved. This deliberately
  replaces ADR-0024's "reconcile later" consequence.
- Recurring Charges annualises from the observed cadence of each merchant's charges (typical charge ×
  365 ÷ median days between charges); a merchant with a single charge shows only what was paid.

## Amendment: named cadences

Recurring Charges names near-standard cadences instead of always showing "Every N days": a median
gap of 6-8 days is Weekly, 12-16 Fortnightly, 28-33 Monthly, 88-94 Quarterly and 360-370 Yearly
(the bands live in `NAMED_CADENCES` in `src/dashboard/queries.py`). A named cadence is projected with
the standard number of charges per year (52, 26, 12, 4, 1) rather than typical × 365 ÷ gap, so a
fortnightly $37.50 charge is $975 a year, not $978. Other gaps keep "Every N days" and the
365 ÷ gap projection. This deviates from the spec's "Every N days" wording; the rows expose the label
as `cadence` (null when not snapped) alongside `cadence_days`.

## Amendment: Top expenses returns

Top merchants is replaced again by **Top expenses**: the largest single Spending Transactions (Expense +
Bills & Subscriptions; Debt and Beem Adjustment excluded), not grouped, ranked by amount: five for a
month, ten for Full year. Grouping by normalised Notes only works when Notes name the merchant, which
is true of Statement Export Transactions but not of the Transactions a user enters by hand, and not
every user imports statements. The merchant key stays, since Recurring Charges still groups by it.
The "Show transaction count" toggle goes with the grouping.
