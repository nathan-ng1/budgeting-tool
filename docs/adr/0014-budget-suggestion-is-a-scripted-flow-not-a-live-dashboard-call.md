# Budget Suggestion generation is a scripted, pluggable-backend flow, not a live call from the Dashboard

The Budget tab (ADR-0013) wants an AI-generated write-up analysing recent Budgeted-vs-Actual history
to help set future Category Budgets. ADR-0004 and ADR-0008 already establish that this project keeps
model-driven judgement calls out of the Dashboard's own request path: categorisation runs through a
scripted `Categoriser` interface with pluggable backends (Claude Code / Codex / an OpenAI-compatible
endpoint), invoked from the terminal, never from the Dashboard web app itself. Budget Suggestion
follows the same shape rather than becoming the first model call the Dashboard triggers live: a
manually-run script (mirroring `uv run python -m statement_export`) generates the write-up through its
own pluggable backend interface and writes it to storage; the Dashboard's Budget tab only ever
displays whatever was last generated.

A live "Generate suggestions" button in the Dashboard was considered and rejected: it's more
immediate, but it would be a first, unreviewed crack in the boundary ADR-0008 draws between the
Dashboard (a passive local viewer/editor over already-computed data) and every model-driven flow in
this project (scripted, chat-adjacent, run deliberately). Keeping Budget Suggestion scripted preserves
that boundary rather than eroding it for one feature's convenience.

The backend selection is its own setting, `ADVISOR_BACKEND`, separate from `CATEGORISER_BACKEND` —
categorising a Transaction and analysing months of Budgeted-vs-Actual history are different-shaped
judgement calls, and nothing requires the same backend/model to be good at both.

## Consequences

- Budget Suggestion has no "last updated" trigger tied to new Transactions arriving — it's stale until
  someone deliberately re-runs the script, the same staleness model Category Budgets themselves already
  have (edited directly, no automatic recompute).
- A future ADR would be needed to cross ADR-0008's boundary deliberately (a live Dashboard-triggered
  model call) — this decision is not that, and shouldn't be read as a first step toward it.
