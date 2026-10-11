import { useState } from "react";

import { categoryColours } from "../lib/categoryColours.js";
import { useMoney } from "../lib/settings.jsx";

// Spending grouped by merchant (Notes normalised as History Match does), ranked
// by total. `merchants` arrives ranked from the backend; `count` is how many
// rows the period shows. `colourFor` is the period's shared Category colour
// mapping (categoryColours). The transaction-count column is a component-local,
// unpersisted toggle.
export default function TopMerchants({ merchants, count, colourFor = categoryColours([]) }) {
  const { money } = useMoney();
  const [showCount, setShowCount] = useState(false);
  const rows = merchants.slice(0, count);
  const largest = rows.length > 0 ? rows[0].total : 0;

  return (
    <section className="card">
      <div className="card__head">
        <h3>Top merchants</h3>
        <label className="toggle">
          <input type="checkbox" checked={showCount} onChange={(event) => setShowCount(event.target.checked)} />
          Show transaction count
        </label>
      </div>

      {rows.length === 0 ? (
        <p className="state">No spending recorded for this period.</p>
      ) : (
        <div className="top5">
          {rows.map((row, index) => (
            <div
              key={`${index}-${row.merchant}`}
              className={`top5__row top5__row--merchant${showCount ? " top5__row--with-count" : ""}`}
            >
              <span className="top5__rank numeric">{String(index + 1).padStart(2, "0")}</span>
              <div className="top5__detail">
                <span className="top5__notes" title={row.merchant}>
                  {row.merchant}
                </span>
                <span className="top5__category">
                  <span className="dot dot--sm" style={{ background: colourFor(row.category) }} />
                  {row.category}
                </span>
                <span className="top5__bar">
                  <span
                    data-testid="merchant-bar"
                    style={{
                      width: `${largest > 0 ? Math.max(0, (row.total / largest) * 100) : 0}%`,
                      background: colourFor(row.category),
                    }}
                  />
                </span>
              </div>
              {showCount && <span className="top5__count numeric muted">{row.count} {"×"}</span>}
              <span className="top5__amount numeric">{money(row.total)}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
