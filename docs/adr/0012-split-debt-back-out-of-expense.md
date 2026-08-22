# Split Debt back out of Expense as its own Type

ADR-0006 folded the old Debt Category into Expense, reasoning that only four Categories ever had
real historical data and a fifth top-level split wasn't worth the complexity. That data has since
grown: Mortgage Repayment is now a real, ongoing, non-discretionary outflow (14 historical
Transactions, two active Recurring Transactions Config rules) that's economically distinct from
day-to-day spend — it converts cash into home equity rather than consuming it, closer in kind to a
Transfer than an Expense, but non-discretionary and paid to an external lender rather than an
account the user controls. **Debt** becomes a fourth Type, alongside Income, Expense, and Transfer,
scoped during a `/grill-with-docs` session. Mortgage Repayment moves from Expense to Debt; the whole
repayment is Debt, including any interest bundled into it, since the Statement Export carries no
principal/interest split to divide it by. Net Balance's formula changes to
`Income − Expenses − Debt`.

## Consequences

- ADR-0006's rationale (only four Categories ever had real data) is superseded for this one
  Category now that Debt has ongoing real data — the rest of ADR-0006 (flat Category list under a
  fixed Type, three-Type collapse for Income/Expense/Transfer) stands.
- Historical Transaction Log rows and Recurring Transactions Config rows already typed
  Expense/Mortgage Repayment need a one-off retype to Debt/Mortgage Repayment — not something
  future rows need, since the categorisation backend now offers Debt directly.
- Budgeted vs Actual and Category Budget stay Expense-only — Category Budget was never extended to
  Debt in this pass; a Category Budget for a Debt Category is out of scope until asked for.
- Spending by Category, Top Expenses, and Expenses over time stay Expense-only, so Debt is now
  invisible to those three views by design — a new Debt-only view was added instead of folding
  Debt into any of them.
