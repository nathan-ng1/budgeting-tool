# Past categorisations are reused: History Matches skip the backend, and history goes into the prompt

Every Statement Export run started categorisation from scratch. The backend saw only the new
Transactions and the Category list, so the same merchants (`TRANSPORTFORNSW OPAL` ×15,
`PAYPAL *GUZMANYGOME` ×7) kept landing in Needs Review even though you'd already decided their
Category many times.

We decided the Transaction Log itself is the memory, used in two ways:

- **Lookup (History Match).** Before calling the backend, each card Statement Export Transaction's
  Notes are normalised (lowercased, digits stripped, whitespace collapsed) and matched exactly
  against the same key over existing Transaction Log rows. If every matching row agrees on one
  Type/Category, the Transaction takes it directly: no backend call and no Needs Review. Only
  misses go to the backend.
- **History in the prompt.** The backend prompt for the misses, for card exports and for outgoing
  Beem rows alike, includes the K = 200 most recently seen normalised Notes keys with their
  Category. A key whose rows disagree is listed with every Category it has had. This is advisory:
  the model can still pick something else or flag Needs Review.

This narrows [ADR-0004](./0004-categorisation-backend-is-pluggable-and-scripted.md)'s framing that
"a fixed rule set can't make that call reliably". A History Match isn't a hand-written rule; it
repeats a judgement already made for that exact merchant. Only genuinely new or ambiguous
Transactions still need a model's judgement.

## Considered Options

- **Prompt history only, no lookup.** Rejected. The model can still flag a well-known merchant as
  Needs Review, so the problem you reported wouldn't be guaranteed to go away, and it costs a
  model call for answers already known.
- **Similarity-score matching for the lookup** (e.g. treating `Woolworths (Carlingford)` and
  `Woolworths Metro (West Pennant Hills)` as one merchant). Rejected for the lookup, because
  different merchants with similar strings (`PAYPAL *UBEREATS` vs `PAYPAL *NETFLIX`) would be
  accepted silently. Near-matches are left to the model through the prompt history.
- **Resolving conflicts by most recent row, or by the last N rows.** Rejected in favour of strict
  agreement: any disagreement, ever, sends the Transaction to the backend. The consequence is
  accepted that a reclassified merchant (e.g. `Gym`, moved from Subscriptions to the Bills &
  Subscriptions Gym Category) never becomes a History Match again.
- **A separate rules table, or recording where each row's Category came from.** Rejected. The
  Transaction Log is already the record you curate on the Dashboard, so fixing a row there is
  enough; there is no second store to keep in sync.

## Consequences

- Every Transaction Log row counts as a correct example, whether the backend, Needs Review, a
  Dashboard edit or a Recurring rule set its Category. A wrong row repeats until you edit it.
- Rows with Category Beem Adjustment are never learned from, by either the lookup or the prompt
  history: direction forced their Category, so they say nothing about what the money was spent on.
- Beem Reports never produce History Matches, because a free-text message like `dinner` is too
  vague to auto-accept. They do get prompt history.
- A run's summary reports how many Transactions were History Matches, how many went to the
  backend, and how many went to Needs Review.
- The prompt grows by up to 200 history lines. That's negligible for the Claude backend; a
  small-context local model (see the openai-compatible notes in
  `docs/agents/statement-export-pipeline.md`) may need a smaller K.
