// The pieces the two Outflows breakdown cards (single month, Full year) share:
// the per-Type legend and the empty-state card.

// `items` are OUTFLOW_SERIES entries plus a `pct` share.
export function OutflowsLegend({ items, testId }) {
  return (
    <div className="allocation__legend" data-testid={testId}>
      {items.map((item) => (
        <span key={item.key} className="allocation__legend-item">
          <span className="dot dot--lg" style={{ background: item.colour }} />
          {item.label} <span className="muted">{item.pct.toFixed(1)}%</span>
        </span>
      ))}
    </div>
  );
}

export function OutflowsEmptyCard({ message }) {
  return (
    <section className="card">
      <div className="card__head">
        <h3>Outflows breakdown</h3>
      </div>
      <p className="state">{message}</p>
    </section>
  );
}
