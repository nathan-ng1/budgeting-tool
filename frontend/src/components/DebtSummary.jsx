import { money } from "../lib/format.js";

// `average` is the Full year view's per-month figure (already divided by
// elapsed months by the backend - see ADR-0011). It is omitted for the
// per-month Overview, where a monthly average makes no sense - same
// convention as StatTiles.
export default function DebtSummary({ debtSummary, total, average }) {
  return (
    <section className="card">
      <div className="card__head">
        <h3>Debt</h3>
        <div className="card__aside">
          <div className="card__aside-figure numeric">{money(total)}</div>
          <div className="card__aside-label">{average !== undefined ? `${money(average)} / month average` : "Total"}</div>
        </div>
      </div>

      {debtSummary.length === 0 ? (
        <p className="state">No Debt repayments recorded for this period.</p>
      ) : (
        <div className="debt-summary">
          <div className="debt-summary__row debt-summary__head">
            <span>Notes</span>
            <span />
            <span className="debt-summary__amount">Amount</span>
          </div>
          {debtSummary.map((row) => (
            <div key={row.notes} className="debt-summary__row">
              <span className="debt-summary__name" title={row.notes}>
                {row.notes}
              </span>
              <div className="debt-summary__bar-track">
                <div className="debt-summary__bar-fill" style={{ width: `${row.pct_of_debt}%` }} />
              </div>
              <span className="debt-summary__amount numeric">{money(row.amount)}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
