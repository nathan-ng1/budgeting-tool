import { generatedAt, signedPct } from "../lib/format.js";
import { toneFor } from "../lib/tone.js";

// Top 6 Expense/Debt rows by trailing variance magnitude, Income excluded -
// the same rows the Budget editor table shows, surfaced here as a quick
// scan ahead of the write-up itself.
function watchlist(editor) {
  if (editor === null) {
    return [];
  }
  return Object.entries(editor)
    .filter(([type]) => type !== "Income")
    .flatMap(([, rows]) => rows)
    .filter((row) => row.average_variance_pct !== null)
    .sort((a, b) => Math.abs(b.average_variance_pct) - Math.abs(a.average_variance_pct))
    .slice(0, 6);
}

// The Advisor is asked for one bullet per line, each starting with "- "
// (advisor.prompt.RESPONSE_INSTRUCTIONS) - strip that marker per line.
// Older write-ups generated before that change are still prose paragraphs
// separated by blank lines, which this degrades to one list item per
// paragraph until they're regenerated.
function bulletsFrom(writeUp) {
  return writeUp
    .split("\n")
    .map((line) => line.trim().replace(/^[-•*]\s+/, ""))
    .filter((line) => line !== "");
}

// The one standing Budget Suggestion write-up (Issue #66) - its own
// top-level card above the Budget tab's editor, not scoped to whichever
// month pill is selected (CONTEXT.md's Budget Suggestion entry). `editor`
// (the currently selected month's rows, or null for Full year) drives the
// variance chips only - the write-up itself is unaffected by month
// selection. `suggestion` is null when the script has never been run.
export default function BudgetSuggestion({ suggestion, editor }) {
  if (suggestion === null) {
    return (
      <section className="card budget-suggestion">
        <h3>Budget Suggestion</h3>
        <p className="state">
          No Budget Suggestion yet — run <code>uv run python -m budget_suggestions</code> to generate one.
        </p>
      </section>
    );
  }

  const chips = watchlist(editor);
  const bullets = bulletsFrom(suggestion.write_up);

  return (
    <section className="card budget-suggestion">
      <div className="card__head">
        <div>
          <h3>Budget Suggestion</h3>
          <p className="card__note">Generated {generatedAt(suggestion.generated_at)}</p>
        </div>
      </div>

      {chips.length > 0 ? (
        <div className="budget-suggestion__chips">
          {chips.map((row) => (
            <span key={row.category} className={`budget-suggestion__chip ${toneFor(row.average_variance_pct)}`}>
              {row.category} {signedPct(row.average_variance_pct)}
            </span>
          ))}
        </div>
      ) : (
        <p className="budget-suggestion__chips-empty">Select a month below to see Category variance chips here.</p>
      )}

      <ul className="budget-suggestion__list">
        {bullets.map((bullet, index) => (
          <li key={index}>{bullet}</li>
        ))}
      </ul>
    </section>
  );
}
