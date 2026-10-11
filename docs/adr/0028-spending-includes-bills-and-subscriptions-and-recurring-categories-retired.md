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
