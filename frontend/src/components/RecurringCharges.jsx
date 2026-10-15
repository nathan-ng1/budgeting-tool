import { categoryColours } from "../lib/categoryColours.js";
import { useDateFormat, useMoney } from "../lib/settings.jsx";

// Every Bills & Subscriptions merchant over the trailing 12 months, ranked by
// projected yearly cost (the backend sends `recurring` already ranked).
// `colourFor` is the period's shared Category colour mapping (categoryColours).
export default function RecurringCharges({ recurring, colourFor = categoryColours([]) }) {
  const { money, preciseMoney } = useMoney();
  const { dayMonth } = useDateFormat();

  return (
    <section className="card">
      <div className="card__head">
        <h3>Bills & Subscriptions</h3>
        <div className="card__aside">
          <div className="card__aside-figure numeric">{money(recurring.per_year)} / year</div>
          <div className="card__aside-label numeric">{money(recurring.per_month)} / month</div>
        </div>
      </div>

      {recurring.rows.length === 0 ? (
        <p className="state">No Bills &amp; Subscriptions recorded in the last 12 months.</p>
      ) : (
        <table className="recurring">
          <thead>
            <tr>
              <th>Merchant</th>
              <th className="recurring__num">Charges</th>
              <th>Last charged</th>
              <th className="recurring__num">Typical</th>
              <th>Cadence</th>
              <th className="recurring__num">Per year</th>
            </tr>
          </thead>
          <tbody>
            {recurring.rows.map((row, index) => (
              <tr key={`${index}-${row.merchant}`}>
                <td>
                  <span data-testid="recurring-merchant" className="recurring__merchant" title={row.merchant}>
                    {row.merchant}
                  </span>
                  <span className="recurring__category muted">
                    <span className="dot dot--sm" style={{ background: colourFor(row.category) }} />
                    {row.category}
                  </span>
                </td>
                <td className="recurring__num numeric">{row.charges}</td>
                <td className="numeric">{dayMonth(row.last_charged)}</td>
                <td className="recurring__num numeric">{preciseMoney(row.typical)}</td>
                <td>
                  {row.cadence_days === null ? (
                    <span className="muted">{row.charges === 1 ? "1 charge" : `${row.charges} charges`}</span>
                  ) : (
                    (row.cadence ?? `Every ${row.cadence_days} days`)
                  )}
                </td>
                <td className="recurring__num numeric">{money(row.per_year)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
