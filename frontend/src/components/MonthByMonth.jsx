import { MONTH_LABELS_LONG } from "../lib/months.js";
import { money, signedMoney } from "../lib/format.js";
import { toneFor } from "../lib/tone.js";

// A balanced month is neither a surplus nor a shortfall, so it reads as a
// plain $0 rather than a signed one - same convention as StatTiles' Available
// to Save tile.
function AvailableToSaveCell({ value }) {
  return (
    <td className={`mbm__num numeric ${toneFor(-value)}`}>{value === 0 ? money(0) : signedMoney(value)}</td>
  );
}

export default function MonthByMonth({ months }) {
  const totalIncome = months.reduce((sum, m) => sum + m.income, 0);
  const totalExpenses = months.reduce((sum, m) => sum + m.expenses, 0);
  const totalBillsSubscriptions = months.reduce((sum, m) => sum + m.bills_subscriptions, 0);
  const totalDebt = months.reduce((sum, m) => sum + m.debt, 0);
  const totalAvailableToSave = months.reduce((sum, m) => sum + m.available_to_save, 0);
  const totalSaved = months.reduce((sum, m) => sum + m.saved, 0);

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
              Bills & Subscriptions
            </th>
            <th scope="col" className="mbm__num">
              Debt
            </th>
            <th scope="col" className="mbm__num">
              Available to Save
            </th>
            <th scope="col" className="mbm__num">
              Saved
            </th>
          </tr>
        </thead>
        <tbody>
          {months.map((m) => (
            <tr key={`${m.year}-${m.month}`} className="mbm__row">
              <td className="mbm__name">{MONTH_LABELS_LONG[m.month - 1]}</td>
              <td className="mbm__num numeric">{money(m.income)}</td>
              <td className="mbm__num numeric">{money(m.expenses)}</td>
              <td className="mbm__num numeric">{money(m.bills_subscriptions)}</td>
              <td className="mbm__num numeric">{money(m.debt)}</td>
              <AvailableToSaveCell value={m.available_to_save} />
              <td className="mbm__num numeric muted">{money(m.saved)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="mbm__row mbm__total">
            <td className="mbm__name">Total</td>
            <td className="mbm__num numeric">{money(totalIncome)}</td>
            <td className="mbm__num numeric">{money(totalExpenses)}</td>
            <td className="mbm__num numeric">{money(totalBillsSubscriptions)}</td>
            <td className="mbm__num numeric">{money(totalDebt)}</td>
            <AvailableToSaveCell value={totalAvailableToSave} />
            <td className="mbm__num numeric muted">{money(totalSaved)}</td>
          </tr>
        </tfoot>
      </table>
    </section>
  );
}
