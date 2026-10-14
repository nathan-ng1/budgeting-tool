# Goals are a locked Savings Category, and a contribution is a Transaction linked to its Goal

A Goal is a savings target with a deadline, tracked on its own Dashboard tab. We decided a
contribution is not a new kind of record: it is an ordinary Savings-Type Transaction in a new,
predefined, **locked** Category named **Goals**, carrying a nullable link to the Goal it funds. A
Goal's saved amount is the sum of its linked contributions, whatever their dates. The alternative,
a separate contributions table, would have put saved money outside the Transaction Log, so the
Saved tile, Available to Save, Unallocated and Category Budgets would each need a second source and
could disagree. As Transactions, contributions are counted everywhere Savings already is, with no
change to those figures.

The Goals Category reuses the `locked` flag that Beem Adjustment introduced
([ADR-0015](./0015-beem-adjustment-reduces-expense-instead-of-income.md)): it can't be renamed,
deleted or have its emoji edited, the categorisation backend never assigns it, and Import refuses it.
Locked does not hide a Category from the Transactions form or the Budget editor, so Goals is
selectable and budgetable like any other Savings Category. What makes Goals special is the link
rule, enforced in the store and not only the frontend: a Transaction has a Goal if and only if its
Category is Goals, the Goal must exist, and a new link may only point at an active Goal.

## Considered Options

- **A separate contributions table.** Rejected, as above.
- **Savings Transactions matched to Goals by Notes or date range.** Rejected: fragile, and a Goal's
  saved amount would change when an unrelated row's Notes were edited.
- **Per-Goal Categories under Savings.** Rejected: Category Management would fill with
  Goal-named Categories that outlive their Goal, and Goals could not be renamed without renaming a
  Category.

## Consequences

- Extends [ADR-0022](./0022-rename-transfer-to-savings-with-predefined-categories.md), which said
  Savings Categories "must stay freely editable, unlike Beem Adjustment": Savings and Investments
  still are, but Goals is a locked Category inside Savings. The Savings Type is still never
  assigned by the categorisation backend, but its "entered by hand via the Transactions tab or
  Recurring Transactions Config" no longer covers Goals rows, which are created from the Goals tab
  or the Transactions tab and are excluded from Recurring Transactions Config.
- Extends [ADR-0010](./0010-transactions-tab-is-per-financial-year-with-client-side-filtering.md)
  and [ADR-0021](./0021-financial-year-switcher-and-calendar-year-toggle.md): the Goals tab is a
  fifth tab that does not use the Financial Year/Calendar Year switcher, because a Goal's saved
  amount and deadline are not tied to a year. Its figures come from their own endpoint, not from the
  one-year Transactions load.
- A new `goals` table, a nullable link column on `transactions` and the seeded Goals Category are
  delivered to existing installs by one guarded migration
  ([ADR-0025](./0025-update-runs-pending-migrations-tracked-in-the-database.md)). The Dashboard
  refuses to start while migrations are pending, since a missing column would otherwise fail every
  Transactions read; it does not run them itself, keeping updates manual
  ([ADR-0019](./0019-update-checks-are-automatic-updates-are-manual.md)).
- Known limitation: re-pointing a Recurring-generated Savings row at a Goal and also editing its
  Notes lets the next Run now re-create the original row, because dedupe keys on Date + Amount +
  Notes. This already happens for any Notes edit on a generated row. Rows don't record where they
  came from, so there is no warning.
- Contributions keep counting toward a Goal after it is archived or deleted; Goals are soft-deleted
  and nothing ever removes a contribution.
