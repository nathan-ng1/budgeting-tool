import { useMoney } from "../lib/settings.jsx";
import { OUTFLOW_SERIES as SERIES } from "../lib/typeColours.js";
import { OutflowsEmptyCard, OutflowsLegend } from "./OutflowsLegend.jsx";

// Below this share a segment is too narrow to hold its amount legibly; the
// amount stays available on hover.
const MIN_LABEL_WIDTH_PCT = 7;

const SCALE = [0, 25, 50, 75, 100];

export default function OutflowsBreakdown({ tiles }) {
  const { money } = useMoney();
  const total = SERIES.reduce((sum, s) => sum + tiles[s.key], 0);

  if (total <= 0) {
    return <OutflowsEmptyCard message="No outflows recorded for this month." />;
  }

  const items = SERIES.map((s) => ({ ...s, amount: tiles[s.key], pct: (tiles[s.key] / total) * 100 }));

  return (
    <section className="card">
      <div className="card__head">
        <h3>Outflows breakdown</h3>
        <OutflowsLegend items={items} testId="outflows-legend" />
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
