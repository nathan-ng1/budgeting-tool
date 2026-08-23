# Beem Adjustment reduces Expense instead of counting as Income

Beem Adjustment was originally modelled as Type Income — a positive-Amount Beem Report row (money
coming to the user) was written deterministically as `Type: Income, Category: Beem Adjustment` per
[ADR-0003](./0003-beem-direction-and-row-filtering-happens-in-the-sanitising-script.md). In
practice, every incoming Beem Adjustment is a reimbursement for a shared or prior Expense (e.g. a
friend paying back their share of a dinner already recorded as an Expense) — not a standalone
earning. Modelling it as Income overstated both Income and Expense at once, instead of netting the
reimbursement against the Expense it offsets. Beem Adjustment becomes a Category under Expense
instead, stored with a negative Amount — a narrow, Category-specific exception to the Transaction
Log's Amount-always-positive rule — so every existing `SUM(Amount)`-based Expense aggregation (Net
Balance, Budgeted vs Actual, the Budget tab's per-Type Total rows) nets it out automatically with no
special-casing needed at any of those sites. Scoped during a `/grill-with-docs` session.

## Consequences

- The Transaction Log's Amount is documented as always positive "regardless of the Statement
  Export's sign" (see CONTEXT.md). Beem Adjustment is now a deliberate, narrow exception to that
  rule — not a general mechanism other Categories can opt into.
- The write path normalises every Statement-Export-sourced Candidate's Amount to positive via
  `abs()`; this needed a Category-specific exception so Beem Adjustment's negative sign survives to
  storage, rather than a general "signed Candidate" abstraction.
- Beem Adjustment is excluded from the categorisation backend's assignable Category list (the
  prompt), even though it remains a valid Expense Category for validity-checking elsewhere — it must
  only ever be produced by the deterministic Beem parser path (ADR-0003), never model-assigned to an
  ordinary card transaction. A mis-assignment there would silently store a real Expense as a
  negative-Amount reduction instead of an addition.
- The 63 existing Transaction Log rows with Category=Beem Adjustment (previously Type Income,
  positive Amount, totalling $4,134.77) are migrated in place to Type Expense with a negated Amount —
  a one-off retype, not something future rows need. This retroactively changes past months' Income
  and Expense totals on the Overview and Budgeted vs Actual views.
- Negative-Amount Beem Report rows (money the user sent) are unaffected — they still fall through to
  normal categorisation as an ordinary Expense, same as before.
