# Retire Refund; positive-Amount card rows are always Bill Payment

[ADR-0007](./0007-classify-refunds-vs-bill-payments-via-the-categorisation-backend.md) added a
categorisation-backend judgement call to distinguish a genuine Refund (`Type: Income, Category:
Refund`) from a Bill Payment on positive-Amount card Statement Export rows, anticipating that Refund
would need dedicated tracking. No real Refund has ever occurred in the live Transaction Log — ADR-
0007 itself flagged this as unverified — and the practical workflow for a merchant credit is manual:
the user simply removes or adjusts the original Expense Transaction it corresponds to, rather than
needing a separate offsetting entry recorded. Refund is retired as a Category, and every
positive-Amount card Statement Export row is now unconditionally treated as a Bill Payment — dropped
deterministically, the same row-type-filtering shape as the Beem Report's own filtering
([ADR-0003](./0003-beem-direction-and-row-filtering-happens-in-the-sanitising-script.md)), rather
than a per-transaction model judgement call. This supersedes ADR-0007. Scoped during the same
`/grill-with-docs` session as
[ADR-0015](./0015-beem-adjustment-reduces-expense-instead-of-income.md).

## Consequences

- The categorisation backend's structured-output schema loses the `is_bill_payment` classification
  axis and the positive-Amount guidance prompt text — positive-Amount card rows are filtered out
  before ever reaching the categorisation backend, mirroring how Beem Report row-type filtering
  already happens deterministically rather than via a model call.
- Refund is removed from the Income Category list; CONTEXT.md's Category list, Refund, Beem Report,
  and Bill Payment term definitions are updated accordingly.
- No historical migration is needed — zero live Transaction Log rows have Category=Refund.
- If a genuine merchant refund needs to be tracked again in future, the user's own workflow is to
  remove or adjust the original Expense Transaction directly via the Dashboard's Transactions tab,
  rather than recording a separate offsetting entry.
