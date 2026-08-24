import { CIRCUMFERENCE, DONUT_RADIUS, donutSegments } from "../lib/charts.js";
import { money } from "../lib/format.js";

const DONUT_THICKNESS = 22;

export default function SpendingByCategory({ spending, total }) {
  const segments = donutSegments(spending);

  return (
    <section className="card">
      <h3>Spending by Category</h3>

      <div className="donut">
        <svg viewBox="0 0 200 200" role="img" aria-label={`Spending by Category, ${money(total)} total`}>
          {/* The track behind the arcs - on a month with no spending it is all
              that shows, which is the empty state rather than a broken chart. */}
          <circle
            cx="100"
            cy="100"
            r={DONUT_RADIUS}
            fill="none"
            stroke="var(--color-neutral-200)"
            strokeWidth={DONUT_THICKNESS}
          />
          {segments
            .filter((segment) => segment.length > 0)
            .map((segment) => (
              <circle
                key={segment.category}
                cx="100"
                cy="100"
                r={DONUT_RADIUS}
                fill="none"
                stroke={segment.colour}
                strokeWidth={DONUT_THICKNESS}
                strokeDasharray={`${segment.length} ${CIRCUMFERENCE}`}
                strokeDashoffset={segment.offset}
              />
            ))}
        </svg>
        <div className="donut__centre">
          <div className="donut__total numeric">{money(total)}</div>
          <div className="donut__caption">total spend</div>
        </div>
      </div>

      {segments.length === 0 ? (
        <p className="state">No expenses recorded for this month.</p>
      ) : (
        <div className="legend">
          {segments.map((segment) => (
            <div key={segment.category} className="legend__row">
              <span className="dot" style={{ background: segment.colour }} />
              <span className="legend__name">{segment.category}</span>
              <span className="legend__amount numeric">{money(segment.amount)}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
