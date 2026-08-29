# Rename Type Transfer to Savings, give it predefined default Categories, and keep it out of automated categorisation

[ADR-0006](./0006-simplify-to-three-types-with-a-flat-category-list.md) introduced Transfer as the
umbrella Type for the old Savings and Investments Categories, populated lazily like every other
rarely-used Category. In practice, the only Transfer Transaction ever recorded (a $1000 transfer,
Category "Savings") was entered by hand — Transfer's Type name never matched what the user actually
calls this money, and starting with zero predefined Categories meant even picking a Category for it
required creating one first. This renames the Type back to **Savings**, seeds it with two
predefined default Categories (**Savings**, **Investments**) instead of waiting for lazy
population — the only Type given this exception, since (unlike Debt, which varies person to
person) every user has some form of savings or investment account — and keeps Savings deliberately
excluded from the categorisation backend and Needs Review: a Savings Transaction still must be
entered by hand via the Dashboard, exactly as before, just now with Categories already there to
pick from. Net Balance's formula (`Income − Expenses − Debt`) is unchanged — Savings still isn't
subtracted — but its Dashboard subtext is corrected from "excludes transfers" to "includes
savings", since money moved to savings was always counted toward the leftover figure, never
subtracted from it; the old wording just described that backwards.

## Consequences

- Supersedes ADR-0006's naming of this Type as Transfer and its lazy-population policy for it.
  Debt, Rental, and Rental Expense keep lazy population as before — this exception is scoped to
  Savings only.
- The pre-existing "Savings" Category (id 346) keeps its name, so Type Savings now contains a
  Category also named Savings, alongside the new Investments Category — an intentional, accepted
  overlap, not a rename target.
- The live database's one existing Transfer Transaction and its Category are migrated to Savings
  by a one-off script (matching `src/migration/categories_table.py`'s pattern), not an automatic
  fix-up on every `connect()`.
- `types_with_categories()`'s current rule — a Type is offered to the categorisation backend and
  Needs Review only if it has any Categories — stops holding for Savings once it has predefined
  Categories. A new, separate exclusion is needed so Savings stays manual-entry-only without also
  blocking rename/delete in Category Management, which is what would happen if this reused
  `Category.locked` (which conflates AI-exclusion with rename/delete-locking, and Savings/
  Investments must stay freely editable, unlike Beem Adjustment).
- Dashboard label changes: the Overview "Transferred" stat tile and the Income Allocation bar/
  sentence become "Saved"; the corresponding backend field names (`tiles.transferred` →
  `tiles.saved`, `transferred_amount`/`transferred_pct` → `saved_amount`/`saved_pct`) and the
  `--color-transfer` CSS variable are renamed to match.
