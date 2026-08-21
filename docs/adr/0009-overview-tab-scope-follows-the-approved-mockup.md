# The Overview tab's scope follows the approved mockup, not ADR-0008's original tab list

ADR-0008 scoped the Dashboard's initial build to "the Overview tab (stat tiles, spending-by-category
donut, expenses-over-time chart) plus Recurring Transactions Config editing," and named Budget as a
later-phase tab. A completed Claude Design mockup for the per-month Overview screen (tracked under
Issue #21) adds three sections beyond that list, inside Overview itself rather than a separate tab: an
income-allocation bar ("Where did my income go?" — Expenses/Transferred/Remaining as a % of Income),
a Budgeted vs Actual table (per-Category Expected vs Actual spend), and a Top 5 expenses list. Rather
than carve these into a later-phase Budget tab, the approved mockup is now the source of truth for what
the per-month Overview tab contains.

This introduces a domain concept that didn't previously exist: a **Category Budget** — a flat monthly
target Amount per Expense Category, edited directly (no history/versioning), used only to populate the
Budgeted vs Actual table's Expected column.

## Consequences

- ADR-0008's tab-scope sentence is superseded for the per-month Overview tab by this ADR; ADR-0008's
  architectural decision (local web app, not a hosted Artifact) is unchanged.
- The Category Budget concept needs its own storage (a new table alongside `transactions` and
  `recurring_rules`) and, eventually, a formal glossary entry in `CONTEXT.md` — flagged here for a
  future `/domain-modeling` pass rather than defined informally.
- The annual Overview (no month selected) is a separate, not-yet-designed screen — this ADR and the
  mockup it references cover the per-month view only.
