import { generatedAt } from "../lib/format.js";

// The one standing Budget Suggestion write-up (Issue #66) - rendered
// underneath the Budget tab's table/grid regardless of which month pill is
// selected, since it isn't scoped to any particular month (CONTEXT.md's
// Budget Suggestion entry). `suggestion` is null when the script has never
// been run.
export default function BudgetSuggestion({ suggestion }) {
  return (
    <section className="budget-suggestion">
      <h4 className="budget-suggestion__heading">Budget Suggestion</h4>
      {suggestion === null ? (
        <p className="state">
          No Budget Suggestion yet — run <code>uv run python -m budget_suggestions</code> to generate one.
        </p>
      ) : (
        <>
          {/* Whatever the store returns is rendered as-is - no client-side
              reformatting, summarising, or truncation of the write-up. */}
          <p className="budget-suggestion__write-up">{suggestion.write_up}</p>
          <p className="card__note">Generated {generatedAt(suggestion.generated_at)}</p>
        </>
      )}
    </section>
  );
}
