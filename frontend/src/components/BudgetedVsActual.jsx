import { colourForCategory } from "../lib/categoryColours.js";
import { money, signedMoney, signedPct } from "../lib/format.js";
import { toneFor } from "../lib/tone.js";

const UNSET = "—";

// The endpoint reports `diff` as budget remaining (expected - actual) and `pct`
// as actual as a share of expected. The table reads the other way round, the
// way the mockup shows it: Diff is what was overspent, so a positive figure is
// over budget. Both are the same number re-signed - no new figure is derived.
function overspend(row) {
  if (row.expected === null) {
    return { diff: null, pct: null };
  }
  return { diff: -row.diff, pct: row.pct - 100 };
}

function SignedCells({ diff, pct }) {
  if (diff === null) {
    return (
      <>
        <td className="bva__num muted">{UNSET}</td>
        <td className="bva__num muted">{UNSET}</td>
      </>
    );
  }

  const tone = toneFor(diff);
  return (
    <>
      <td className={`bva__num numeric ${tone}`}>{signedMoney(diff)}</td>
      <td className={`bva__num numeric ${tone}`}>{signedPct(pct)}</td>
    </>
  );
}

export default function BudgetedVsActual({ rows }) {
  // The mockup orders this table by spend so it reads alongside the donut
  // legend next to it; the endpoint returns it alphabetically.
  const ordered = [...rows].sort((a, b) => b.actual - a.actual || a.category.localeCompare(b.category));

  // The Total row compares like with like: only Categories that actually have
  // a Category Budget count, on BOTH sides. Charging an unbudgeted Category's
  // spend against a budgeted-only Expected would read as an overspend that
  // isn't one - an unset Category Budget is not a $0 one (CONTEXT.md).
  const budgeted = ordered.filter((row) => row.expected !== null);
  const totalExpected = budgeted.reduce((sum, row) => sum + row.expected, 0);
  const totalActual = budgeted.reduce((sum, row) => sum + row.actual, 0);
  const totalDiff = totalActual - totalExpected;
  const totalPct = totalExpected > 0 ? (totalActual / totalExpected) * 100 - 100 : null;

  return (
    <section className="card card--chart">
      <div className="card__head">
        <h3>Budgeted vs Actual</h3>
        {budgeted.length > 0 && (
          <div className="card__aside">
            <div className={`card__aside-figure numeric ${toneFor(totalDiff)}`}>
              {signedMoney(totalDiff)}
            </div>
            <div className="card__aside-label">Difference</div>
          </div>
        )}
      </div>

      {ordered.length === 0 ? (
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
                Expected
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
          <tbody>
            {ordered.map((row) => {
              const { diff, pct } = overspend(row);
              return (
                <tr key={row.category} className="bva__row">
                  <td>
                    <span className="dot" style={{ background: colourForCategory(row.category) }} />
                  </td>
                  <td>{row.category}</td>
                  <td className="bva__num numeric muted">
                    {row.expected === null ? UNSET : money(row.expected)}
                  </td>
                  <td className="bva__actual numeric">{money(row.actual)}</td>
                  <SignedCells diff={diff} pct={pct} />
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr className="bva__row bva__total">
              <td />
              <td style={{ fontWeight: 600 }}>Total</td>
              <td className="bva__num numeric muted">{budgeted.length > 0 ? money(totalExpected) : UNSET}</td>
              <td className="bva__actual numeric">{money(totalActual)}</td>
              <SignedCells diff={totalPct === null ? null : totalDiff} pct={totalPct} />
            </tr>
          </tfoot>
        </table>
      )}
    </section>
  );
}
