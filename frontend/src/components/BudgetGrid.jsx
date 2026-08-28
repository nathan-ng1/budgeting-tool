import { gridTotalsByType } from "../lib/budgetTotals.js";
import { monthsOfPeriod } from "../lib/period.js";
import { money } from "../lib/format.js";

// The Budget tab's Full year read-only grid (Issue #64) - every Category's
// Category Budget across the shared referenceYear's 12 months, in the shared
// periodType's framing (ADR-0021: Jul-Jun for Financial Year, Jan-Dec for
// Calendar Year), grouped by Type. Deliberately plain <td> cells, not inputs:
// this view has no editing surface at all, unlike Budget.jsx's per-month
// editor table it sits alongside.
export default function BudgetGrid({ referenceYear, periodType, grid }) {
  const totals = gridTotalsByType(grid);

  return (
    <div className="table-scroll">
      <table className="table">
        <thead>
          <tr>
            <th scope="col">Category</th>
            {monthsOfPeriod(referenceYear, periodType).map(({ year, month, label }) => (
              <th key={`${year}-${month}`} scope="col" className="table__num">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        {Object.entries(grid).map(([type, rows]) => (
          <tbody key={type}>
            <tr>
              <th scope="colgroup" colSpan={13} className="table__section">
                {type}
              </th>
            </tr>
            {rows.map(({ category, amounts }) => (
              <tr key={category}>
                <td>{category}</td>
                {amounts.map((amount, index) => (
                  <td key={index} className="table__num muted">
                    {amount === null ? "" : money(amount)}
                  </td>
                ))}
              </tr>
            ))}
            <tr className="budget__total-row">
              <td>Total</td>
              {totals[type].map((amount, index) => (
                <td key={index} className="table__num">
                  {money(amount)}
                </td>
              ))}
            </tr>
          </tbody>
        ))}
      </table>
    </div>
  );
}
