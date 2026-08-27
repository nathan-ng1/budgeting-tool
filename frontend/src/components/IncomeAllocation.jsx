import { allocationBar } from "../lib/allocationBar.js";
import { money } from "../lib/format.js";

const SEGMENT_COLOURS = {
  expenses: "var(--color-negative-fill)",
  debt: "var(--color-debt)",
  transferred: "var(--color-transfer)",
  remaining: "var(--color-accent-2-500)",
  over_income: "var(--color-danger)",
};

export default function IncomeAllocation({ allocation, income }) {
  const bar = allocationBar(allocation);

  // With no Income there is nothing to take a share of, so the endpoint zeroes
  // every percentage. Rendering that as "Expenses 0.0%" beside an empty bar
  // would read as "nothing was spent" even when plenty was - say so instead.
  if (income <= 0) {
    const outflow = allocation.expenses_amount + allocation.debt_amount + allocation.transferred_amount;
    return (
      <section className="card">
        <div className="card__head">
          <h3>Where did my income go?</h3>
        </div>
        <p className="state">
          {outflow > 0
            ? `No income recorded for this month, against ${money(allocation.expenses_amount)} of expenses, ${money(
                allocation.debt_amount,
              )} of debt repayments, and ${money(allocation.transferred_amount)} transferred.`
            : "No income recorded for this month."}
        </p>
      </section>
    );
  }

  return (
    <section className="card">
      <div className="card__head">
        <h3>Where did my income go?</h3>
        <div className="allocation__legend">
          {bar.segments.map((segment) => (
            <span key={segment.key} className="allocation__legend-item">
              <span className="dot dot--lg" style={{ background: SEGMENT_COLOURS[segment.key] }} />
              {segment.label}{" "}
              <span className="muted">
                {segment.key === "over_income" ? money(segment.amount) : `${segment.pct.toFixed(1)}%`}
              </span>
            </span>
          ))}
        </div>
      </div>

      <div className="allocation__bar-wrap">
        <div className="allocation__bar">
          {bar.segments.map((segment) => (
            <div
              key={segment.key}
              className="allocation__segment"
              style={{ width: segment.width, background: SEGMENT_COLOURS[segment.key] }}
            />
          ))}
        </div>
        {/* Where 100% of Income sits - it moves in from the right edge when
            outflows ran past income and stretched the axis. */}
        <div className="allocation__marker" style={{ left: bar.incomeMarkerLeft }} />
      </div>

      <div className="allocation__ticks">
        {bar.ticks.map((tick) => (
          <span key={tick.label} className="allocation__tick numeric" style={{ left: tick.left }}>
            {tick.label}
          </span>
        ))}
      </div>
    </section>
  );
}
