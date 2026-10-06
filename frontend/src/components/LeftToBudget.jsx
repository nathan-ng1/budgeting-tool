import { OUTFLOW_TYPES, leftToBudget } from "../lib/budgetTotals.js";
import { money } from "../lib/format.js";
import { BalanceChip, BalanceFigure, isShort } from "./BalanceStatus.jsx";

// Left to Budget (Issue #167, see GLOSSARY.md): budgeted Income minus every
// budgeted outflow, Savings included - the planning-time counterpart of the
// Overview's Unallocated, sharing its display rule (spec #164).

// The same fills as the "Where did my income go?" bar's segments
// (IncomeAllocation.jsx), so a Type reads as one colour across both tabs.
const SEGMENT_COLOURS = {
  Expense: "var(--color-negative-fill)",
  "Bills & Subscriptions": "var(--color-bills-subscriptions)",
  Debt: "var(--color-debt)",
  Savings: "var(--color-savings)",
};

// The per-month editor's block, right of the month pills. `totals` is
// totalsByType's live output, so it moves as the user types, before Save.
export function LeftToBudgetSummary({ totals }) {
  const { income, outflows, left } = leftToBudget(totals);
  // The axis spans whichever is larger, so an over-budgeted plan's segments
  // run past the Income marker instead of being clipped at it. The floor of 1
  // just avoids dividing by zero when nothing is budgeted.
  const axis = Math.max(income, outflows, 1);

  return (
    <section className="left-to-budget" aria-label="Left to Budget">
      <div className="tile__label">Left to Budget</div>
      <div className="left-to-budget__value">
        <BalanceFigure value={left} /> <BalanceChip value={left} shortLabel="Over-budgeted" />
      </div>
      <div className="left-to-budget__meter" title="Budgeted outflows against budgeted Income">
        <div className="left-to-budget__track">
          {OUTFLOW_TYPES.map((type) => (
            <div
              key={type}
              className="left-to-budget__segment"
              style={{ width: `${((totals[type] ?? 0) / axis) * 100}%`, background: SEGMENT_COLOURS[type] }}
            />
          ))}
        </div>
        <div className="left-to-budget__marker" style={{ left: `${(income / axis) * 100}%` }} />
      </div>
      <div className="left-to-budget__caption">
        {money(outflows)} of {money(income)} budgeted Income
      </div>
    </section>
  );
}

// The Full year grid's trailing row. `totals` is gridTotalsByType's output
// (one array per Type), read a month column at a time.
export function LeftToBudgetGridRow({ totals, monthCount }) {
  const months = Array.from({ length: monthCount }, (_, index) =>
    leftToBudget(Object.fromEntries(Object.entries(totals).map(([type, amounts]) => [type, amounts[index] ?? 0]))),
  );

  return (
    <tbody>
      <tr className="budget__total-row left-to-budget__row">
        <td>Left to Budget</td>
        {months.map(({ income, outflows, left }, index) => {
          // A month with nothing budgeted is unplanned, not balanced - so it
          // stays blank rather than reading "$0 Balanced" (spec #164).
          if (income === 0 && outflows === 0) {
            return <td key={index} />;
          }
          const share = income > 0 ? Math.min(outflows / income, 1) : 1;
          return (
            <td key={index} className="table__num">
              <BalanceFigure value={left} />
              <div className="left-to-budget__mini-meter">
                <div
                  className={`left-to-budget__mini-fill ${isShort(left) ? "left-to-budget__mini-fill--over" : ""}`.trim()}
                  style={{ width: `${share * 100}%` }}
                />
              </div>
            </td>
          );
        })}
      </tr>
    </tbody>
  );
}
