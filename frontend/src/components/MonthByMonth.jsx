import { MONTH_LABELS_LONG } from "../lib/months.js";
import { money, signedMoney } from "../lib/format.js";
import { toneFor } from "../lib/tone.js";

// A balanced month is neither a surplus nor a shortfall, so it reads as a
// plain $0 rather than a signed one - same convention as StatTiles' Net
// Balance tile.
function NetCell({ value }) {
  return (
    <td className={`mbm__num numeric ${toneFor(-value)}`}>{value === 0 ? money(0) : signedMoney(value)}</td>
  );
}

export default function MonthByMonth({ months }) {
  const totalIncome = months.reduce((sum, m) => sum + m.income, 0);
  const totalExpenses = months.reduce((sum, m) => sum + m.expenses, 0);
  const totalDebt = months.reduce((sum, m) => sum + m.debt, 0);
  const totalNet = months.reduce((sum, m) => sum + m.net_balance, 0);
  const totalTransferred = months.reduce((sum, m) => sum + m.transferred, 0);

  return (
    <section className="card card--chart">
      <div className="card__head">
        <div>
          <h3>Month by month</h3>
        </div>
      </div>

      <table className="mbm">
        <thead>
          <tr className="mbm__row mbm__head">
            <th scope="col" style={{ textAlign: "left" }}>
              Month
            </th>
            <th scope="col" className="mbm__num">
              Income
            </th>
            <th scope="col" className="mbm__num">
              Expenses
            </th>
            <th scope="col" className="mbm__num">
              Debt
            </th>
            <th scope="col" className="mbm__num">
              Net
            </th>
            <th scope="col" className="mbm__num">
              Transfers
            </th>
          </tr>
        </thead>
        <tbody>
          {months.map((m) => (
            <tr key={`${m.year}-${m.month}`} className="mbm__row">
              <td className="mbm__name">{MONTH_LABELS_LONG[m.month - 1]}</td>
              <td className="mbm__num numeric">{money(m.income)}</td>
              <td className="mbm__num numeric">{money(m.expenses)}</td>
              <td className="mbm__num numeric">{money(m.debt)}</td>
              <NetCell value={m.net_balance} />
              <td className="mbm__num numeric muted">{money(m.transferred)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="mbm__row mbm__total">
            <td className="mbm__name">Total</td>
            <td className="mbm__num numeric">{money(totalIncome)}</td>
            <td className="mbm__num numeric">{money(totalExpenses)}</td>
            <td className="mbm__num numeric">{money(totalDebt)}</td>
            <NetCell value={totalNet} />
            <td className="mbm__num numeric muted">{money(totalTransferred)}</td>
          </tr>
        </tfoot>
      </table>
    </section>
  );
}
