# Simplify the budget model to three Types (Income/Expense/Transfer) with a flat Category list

The old model had six top-level Categories (Income, Expenses, Bills & Subscriptions, Savings, Debt, Investments) with a Sub-category underneath each — but a live-sheet check of `Transaction Log!J9:L164` showed Savings, Investments, Rental (Income), and Rental Expense had never actually been used; only four Categories ever saw real data. We collapsed to three **Types** — Income, Expense, Transfer — with a flat **Category** list underneath (Category now means what Sub-category used to mean). Bills & Subscriptions and Debt's Mortgage Repayment fold into Expense; Savings and Investments become the new Transfer Type, populated lazily from real cases rather than speculatively — the same policy the old model already applied to its unused Categories.

## Consequences

- `src/transaction_log/categories.py`'s `SUB_CATEGORIES_BY_CATEGORY` mapping, and every reference to "Category"/"Sub-category" in code, prompts (`src/categorisation/prompt.py`), and docs, need renaming to Type/Category.
- The Transfer Type currently has zero real Categories under it — the first real transfer transaction determines what gets added, not a speculative list written now.
