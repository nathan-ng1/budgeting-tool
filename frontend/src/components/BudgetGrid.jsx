import { monthsOfFinancialYear } from "../lib/financialYear.js";
import { money } from "../lib/format.js";

// The Budget tab's Full year read-only grid (Issue #64) - every Category's
// Category Budget across the Financial Year's 12 months, grouped by Type.
// Deliberately plain <td> cells, not inputs: this view has no editing
// surface at all, unlike Budget.jsx's per-month editor table it sits
// alongside.
export default function BudgetGrid({ financialYear, grid }) {
  return (
    <div className="table-scroll">
      <table className="table">
        <thead>
          <tr>
            <th scope="col">Category</th>
            {monthsOfFinancialYear(financialYear).map(({ year, month, label }) => (
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
          </tbody>
        ))}
      </table>
    </div>
  );
}
