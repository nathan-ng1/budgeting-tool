# Reintroduce Bills & Subscriptions as a fifth fixed Type, with predefined Categories

[ADR-0006](./0006-simplify-to-three-types-with-a-flat-category-list.md) retired "Bills &
Subscriptions" as a top-level classification, folding it into Expense when the old six-Category
model collapsed to a flat Type/Category list. In practice that left irregular, infrequent bills — an
annual insurance premium, car registration, a yearly phone plan renewal — mixed in with ordinary
day-to-day Expense Categories (Groceries, Dining & Takeaway), with no dedicated figure for "how much am
I committed to in recurring bills and subscriptions". This brings the name back, deliberately, as a
fifth fixed **Type** — `TYPE_ORDER = (Income, Expense, Bills & Subscriptions, Debt, Savings)` — rather
than as a Category grouping layer: the flat Type/Category model ADR-0006 introduced stays intact, and
Bills & Subscriptions is simply one more Type in it, with its own Category list underneath.

It follows the precedent [ADR-0022](./0022-rename-transfer-to-savings-with-predefined-categories.md)
set for Savings: four **predefined** Categories — Insurance, Car Registration, Phone Plan, Internet —
seeded for every install rather than populated lazily, since (unlike Debt) every household has some
recurring bills. Unlike Beem Adjustment they're seeded **unlocked**, so Category Management can rename
or delete any of them, and the user can add their own. Unlike Savings, Bills & Subscriptions is **not**
added to `AI_EXCLUDED_TYPES`: a recurring card charge is exactly what a Statement Export contains, so
the categorisation backend may assign its Categories and Needs Review offers them, the same as Income,
Expense, and Debt.

Category Budget applies to it from the start, extending
[ADR-0013](./0013-category-budget-is-per-month-across-income-expense-and-debt.md) and
[ADR-0023](./0023-extend-category-budget-to-savings-categories.md)'s "every Type is budgetable" rule:
the Budget tab's per-month editor and Full year grid show a Bills & Subscriptions section with no
component changes, because both already iterate `TYPE_ORDER`.

## Consequences

- Reverses ADR-0006's folding of Bills & Subscriptions into Expense, but not its flat Type/Category
  model — this is a new Type, not a revived grouping layer between Category and Type.
- The existing Expense Categories "Subscriptions" and "Insurance & Bills" overlap in meaning with the
  new Type. They are deliberately left where they are for now; reconciling them (retyping, merging, or
  retiring them) is a separate, later decision.
- An existing install doesn't pick the new Type up on its own: `database.store._seed_default_categories`
  only seeds an empty `categories` table (so a deliberately deleted Category stays deleted). The four
  Categories reach an existing database via the one-off `src/migration/add_bills_and_subscriptions.py`,
  matching `rename_transfer_to_savings.py`'s pattern, which the update process runs since
  [ADR-0025](./0025-update-runs-pending-migrations-tracked-in-the-database.md). It only seeds while the Type has no Categories at
  all, so a rerun never resurrects a renamed or deleted one, and skips any predefined name a user has
  already created under another Type (Category names are unique across every Type).
- `dashboard.queries.BUDGETABLE_TYPES` — previously a hardcoded set kept in step with
  `dashboard.budgets.BUDGETABLE_TYPES = TYPE_ORDER` by hand — is unified onto `TYPE_ORDER` itself, so a
  future Type is budgetable everywhere the moment it joins `TYPE_ORDER`. The frontend Transactions tab's
  Types filter likewise reuses the frontend `TYPE_ORDER` mirror instead of its own literal list.
- Budget Suggestion's write-up filters rows by excluding Income and Savings, so Bills & Subscriptions
  Categories flow into its analysis alongside Expense and Debt — intended, since they're spending the
  write-up should comment on.
- The Overview tab (Stat Tiles, Net Balance, Income Allocation, the monthly chart and table, Budgeted
  vs Actual) is not Type-agnostic and gains Bills & Subscriptions separately, including Net Balance's
  formula changing to subtract it.
