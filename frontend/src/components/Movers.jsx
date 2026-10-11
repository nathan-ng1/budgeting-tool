import { useState } from "react";

import { signedPct, UNSET } from "../lib/format.js";
import { useMoney } from "../lib/settings.jsx";

// The comparisons the backend carries in one payload, so switching between
// them is a local re-render (no refetch). Order is the dropdown's order.
const BASES = [
  { key: "previous_month", label: "Previous month", phrase: "vs the previous month" },
  { key: "avg_3_months", label: "Avg of preceding 3 months", phrase: "vs the average of the preceding 3 months" },
  { key: "avg_12_months", label: "Avg of preceding 12 months", phrase: "vs the average of the preceding 12 months" },
];
const DEFAULT_BASIS = "avg_3_months";

// How far each Spending Category sits from a chosen comparison (single month
// only). A neutral readout: rising and falling are shown, never judged. The
// backend sends each basis already sorted, largest difference first.
export default function Movers({ movers }) {
  const { signedMoney } = useMoney();
  const [basisKey, setBasisKey] = useState(DEFAULT_BASIS);
  const basis = BASES.find((b) => b.key === basisKey);
  const rows = movers[basisKey];
  // Bars scale to the largest difference and fill at most half the track,
  // either side of the centre line.
  const span = Math.max(...rows.map((row) => Math.abs(row.diff)), 1);

  return (
    <section className="card">
      <div className="card__head">
        <h3>Movers</h3>
        <select
          className="movers__select"
          aria-label="Compare against"
          value={basisKey}
          onChange={(event) => setBasisKey(event.target.value)}
        >
          {BASES.map((b) => (
            <option key={b.key} value={b.key}>
              {b.label}
            </option>
          ))}
        </select>
      </div>

      {rows.length === 0 ? (
        <p className="state">No Spending to compare for this month.</p>
      ) : (
        <div className="movers">
          <div className="movers__head">
            <span />
            <span />
            <span className="movers__num">Difference ($)</span>
            <span className="movers__num">Difference (%)</span>
            <span className="movers__basis">{basis.phrase}</span>
          </div>
          {rows.map((row) => (
            <div key={row.category} className="movers__row" data-testid="mover-row">
              <span className="movers__name" title={row.category}>
                {row.category}
              </span>
              <span className="movers__track">
                <span className="movers__mid" />
                <span
                  className={`movers__bar ${row.diff >= 0 ? "movers__bar--up" : "movers__bar--down"}`}
                  style={{ width: `${(Math.abs(row.diff) / span) * 50}%` }}
                />
              </span>
              <span className="movers__num numeric">{row.diff === 0 ? UNSET : signedMoney(row.diff)}</span>
              <span className="movers__num movers__pct numeric muted">
                {row.diff === 0 ? UNSET : row.pct === null ? "New" : signedPct(row.pct)}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
