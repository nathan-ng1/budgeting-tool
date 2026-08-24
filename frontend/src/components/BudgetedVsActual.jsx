import { colourForCategory } from "../lib/categoryColours.js";
import { UNSET, money, signedMoney, signedPct } from "../lib/format.js";
import { toneFor } from "../lib/tone.js";

// The budgetable Types, in CONTEXT.md's order - the table's section order,
// top to bottom. Deliberately its own list rather than transactionsView.js's
// TYPES (that module is scoped to the Transactions tab, and its list
// includes Transfer, which has no Category Budget to show here).
const SECTIONS = ["Income", "Expense", "Debt"];

// The endpoint reports `diff` as budget remaining (budgeted - actual) and
// `pct` as actual as a share of budgeted. The table reads the other way
// round, the way the mockup shows it: Diff is what was overspent, so a
// positive figure means actual came in above budgeted. Both are the same
// number re-signed - no new figure is derived.
function overspend(row) {
  if (row.budgeted === null) {
    return { diff: null, pct: null };
  }
  // A $0 Category Budget with $0 actual isn't overspend at all - there's
  // nothing to divide, so the endpoint's 0-for-undefined-division fallback
  // would otherwise read as -100%.
  if (row.budgeted === 0 && row.actual === 0) {
    return { diff: -row.diff, pct: 0 };
  }
  return { diff: -row.diff, pct: row.pct - 100 };
}

// For Income, coming in above budgeted is good news, not overspend - the
// opposite of Expense/Debt. The figure itself keeps the same sign either way
// (a positive Diff always means "actual above budgeted"); only which colour
// that reads as flips, the same way MonthByMonth/StatTiles flip tone by
// negating the value they feed toneFor rather than editing toneFor itself.
function toneForType(type, diff) {
  if (diff === null) {
    return "";
  }
  return toneFor(type === "Income" ? -diff : diff);
}

function SignedCells({ type, diff, pct }) {
  if (diff === null) {
    return (
      <>
        <td className="bva__num muted">{UNSET}</td>
        <td className="bva__num muted">{UNSET}</td>
      </>
    );
  }

  const tone = toneForType(type, diff);
  return (
    <>
      <td className={`bva__num numeric ${tone}`}>{signedMoney(diff)}</td>
      <td className={`bva__num numeric ${tone}`}>{signedPct(pct)}</td>
    </>
  );
}

// Budgeted and Diff/% compare like with like: only Categories that actually
// have a Category Budget count. Charging an unbudgeted Category's spend
// against a budgeted-only total would read as an overspend that isn't one -
// an unset Category Budget is not a $0 one (CONTEXT.md). Actual isn't a
// comparison though - it's the section's real total spend/income, so it
// sums every row regardless of budget.
function subtotal(rows) {
  const budgeted = rows.filter((row) => row.budgeted !== null);
  const totalBudgeted = budgeted.reduce((sum, row) => sum + row.budgeted, 0);
  const totalActual = rows.reduce((sum, row) => sum + row.actual, 0);
  const budgetedActual = budgeted.reduce((sum, row) => sum + row.actual, 0);
  const totalDiff = budgetedActual - totalBudgeted;
  const totalPct = totalBudgeted > 0 ? (budgetedActual / totalBudgeted) * 100 - 100 : null;
  return { hasBudgeted: budgeted.length > 0, totalBudgeted, totalActual, totalDiff, totalPct };
}

function Section({ type, rows }) {
  if (rows.length === 0) {
    return null;
  }

  // The mockup orders the table by spend so it reads alongside the donut
  // legend next to it; the endpoint returns it grouped by Type only.
  const ordered = [...rows].sort((a, b) => b.actual - a.actual || a.category.localeCompare(b.category));
  const { hasBudgeted, totalBudgeted, totalActual, totalDiff, totalPct } = subtotal(ordered);

  return (
    <tbody>
      <tr className="bva__row bva__section">
        <th scope="colgroup" colSpan={6}>
          {type}
        </th>
      </tr>
      {ordered.map((row) => {
        const { diff, pct } = overspend(row);
        return (
          <tr key={row.category} className="bva__row">
            <td>
              <span className="dot" style={{ background: colourForCategory(row.category) }} />
            </td>
            <td>{row.category}</td>
            <td className="bva__num numeric muted">{row.budgeted === null ? UNSET : money(row.budgeted)}</td>
            <td className="bva__actual numeric">{money(row.actual)}</td>
            <SignedCells type={type} diff={diff} pct={pct} />
          </tr>
        );
      })}
      <tr className="bva__row bva__total">
        <td />
        <td style={{ fontWeight: 600 }}>{type} total</td>
        <td className="bva__num numeric muted">{hasBudgeted ? money(totalBudgeted) : UNSET}</td>
        <td className="bva__actual numeric">{money(totalActual)}</td>
        <SignedCells type={type} diff={totalPct === null ? null : totalDiff} pct={totalPct} />
      </tr>
    </tbody>
  );
}

export default function BudgetedVsActual({ rows }) {
  // The header's total Diff badge is the same subtotal() shape the per-Type
  // rows already use, just applied across every row rather than one
  // Section's - so it inherits the same "budgeted Categories only" exclusion
  // (Issue #74) without a second computation to keep in sync.
  const { hasBudgeted, totalDiff } = subtotal(rows);

  return (
    <section className="card card--chart">
      <div className="card__head">
        <h3>Budgeted vs Actual</h3>
        {rows.length > 0 && (
          <div className="card__aside">
            <div className={`card__aside-figure numeric ${hasBudgeted ? toneFor(totalDiff) : ""}`}>
              {hasBudgeted ? signedMoney(totalDiff) : UNSET}
            </div>
            <div className="card__aside-label">Total Diff</div>
          </div>
        )}
      </div>

      {rows.length === 0 ? (
        <p className="state">No spending or Category Budgets for this month.</p>
      ) : (
        <table className="bva">
          <thead>
            <tr className="bva__row bva__head">
              <th scope="col" aria-label="Category colour" />
              <th scope="col" style={{ textAlign: "left" }}>
                Category
              </th>
              <th scope="col" className="bva__num">
                Budgeted
              </th>
              <th scope="col" className="bva__num">
                Actual
              </th>
              <th scope="col" className="bva__num">
                Diff
              </th>
              <th scope="col" className="bva__num">
                %
              </th>
            </tr>
          </thead>
          {SECTIONS.map((type) => (
            <Section key={type} type={type} rows={rows.filter((row) => row.type === type)} />
          ))}
        </table>
      )}
    </section>
  );
}
