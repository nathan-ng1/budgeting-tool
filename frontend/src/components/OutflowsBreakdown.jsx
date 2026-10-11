import { useMoney } from "../lib/settings.jsx";
import { TYPE_COLOURS } from "../lib/typeColours.js";

// The three Types that make up Outflows (GLOSSARY.md); Savings is deliberately
// absent - it's what's left to keep, not something spent.
const SERIES = [
  { key: "expenses", label: "Expenses", colour: TYPE_COLOURS.Expense },
  { key: "bills_subscriptions", label: "Bills & Subscriptions", colour: TYPE_COLOURS["Bills & Subscriptions"] },
  { key: "debt", label: "Debt", colour: TYPE_COLOURS.Debt },
];

// Below this share a segment is too narrow to hold its amount legibly; the
// amount stays available on hover.
const MIN_LABEL_WIDTH_PCT = 7;

const SCALE = [0, 25, 50, 75, 100];

export default function OutflowsBreakdown({ tiles }) {
  const { money } = useMoney();
  const total = SERIES.reduce((sum, s) => sum + tiles[s.key], 0);

  if (total <= 0) {
    return (
      <section className="card">
        <div className="card__head">
          <h3>Outflows breakdown</h3>
        </div>
        <p className="state">No outflows recorded for this month.</p>
      </section>
    );
  }

  const items = SERIES.map((s) => ({ ...s, amount: tiles[s.key], pct: (tiles[s.key] / total) * 100 }));

  return (
    <section className="card">
      <div className="card__head">
        <h3>Outflows breakdown</h3>
        <div className="allocation__legend" data-testid="outflows-legend">
          {items.map((item) => (
            <span key={item.key} className="allocation__legend-item">
              <span className="dot dot--lg" style={{ background: item.colour }} />
              {item.label} <span className="muted">{item.pct.toFixed(1)}%</span>
            </span>
          ))}
        </div>
      </div>

      <div className="allocation__bar-wrap">
        <div className="allocation__bar outflows__bar">
          {items.map((item) => (
            <div
              key={item.key}
              data-testid="outflows-segment"
              className="allocation__segment outflows__segment"
              style={{ width: `${item.pct}%`, background: item.colour }}
              title={`${item.label} ${money(item.amount)}`}
            >
              {item.pct >= MIN_LABEL_WIDTH_PCT && money(item.amount)}
            </div>
          ))}
        </div>
      </div>

      <div className="allocation__ticks">
        {SCALE.map((tick) => (
          <span key={tick} className="allocation__tick numeric" style={{ left: `${tick}%` }}>
            {tick}%
          </span>
        ))}
      </div>
    </section>
  );
}
