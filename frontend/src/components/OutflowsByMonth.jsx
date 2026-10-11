import {
  OUTFLOWS_CHART_HEIGHT,
  OUTFLOWS_CHART_WIDTH,
  outflowsColumnsChart,
  plotGridlines,
} from "../lib/charts.js";
import { MONTH_LABELS_SHORT } from "../lib/months.js";
import { useMoney } from "../lib/settings.jsx";
import { TYPE_COLOURS } from "../lib/typeColours.js";

// The three Types that make up Outflows (GLOSSARY.md); Savings is deliberately
// absent. Same series and colours as the single-month OutflowsBreakdown.
const SERIES = [
  { key: "expenses", label: "Expenses", colour: TYPE_COLOURS.Expense },
  { key: "bills_subscriptions", label: "Bills & Subscriptions", colour: TYPE_COLOURS["Bills & Subscriptions"] },
  { key: "debt", label: "Debt", colour: TYPE_COLOURS.Debt },
];

// Full year Outflows breakdown: one stacked column per month, each segment
// labelled with its share of that month's Outflows. The legend gives each
// Type's share of the year to date - percentages only, no dollar amounts.
export default function OutflowsByMonth({ months }) {
  const { money } = useMoney();
  const chart = outflowsColumnsChart(months);
  const yearTotal = SERIES.reduce((sum, s) => sum + months.reduce((acc, m) => acc + m[s.key], 0), 0);

  if (yearTotal <= 0) {
    return (
      <section className="card">
        <div className="card__head">
          <h3>Outflows breakdown</h3>
        </div>
        <p className="state">No outflows recorded for this period.</p>
      </section>
    );
  }

  const legend = SERIES.map((s) => ({
    ...s,
    pct: (months.reduce((acc, m) => acc + m[s.key], 0) / yearTotal) * 100,
  }));
  const seriesByKey = Object.fromEntries(SERIES.map((s) => [s.key, s]));

  return (
    <section className="card card--chart">
      <div className="card__head">
        <h3>Outflows breakdown</h3>
        <div className="allocation__legend" data-testid="outflows-columns-legend">
          {legend.map((item) => (
            <span key={item.key} className="allocation__legend-item">
              <span className="dot dot--lg" style={{ background: item.colour }} />
              {item.label} <span className="muted">{item.pct.toFixed(1)}%</span>
            </span>
          ))}
        </div>
      </div>

      <div className="outflows-cols">
        <div className="outflows-cols__yaxis numeric">
          {chart.yTicks.map((tick, index) => (
            <span
              key={tick}
              className="timechart__ylabel"
              style={{ top: `${(index / (chart.yTicks.length - 1)) * 100}%` }}
            >
              {money(tick)}
            </span>
          ))}
        </div>

        <div className="outflows-cols__plot">
          <svg
            viewBox={`0 0 ${OUTFLOWS_CHART_WIDTH} ${OUTFLOWS_CHART_HEIGHT}`}
            preserveAspectRatio="none"
            role="img"
            aria-label="Outflows by Type for every month of the period, as stacked columns"
          >
            <g stroke="var(--color-neutral-300)" strokeWidth="1" vectorEffect="non-scaling-stroke">
              {plotGridlines(OUTFLOWS_CHART_HEIGHT).map((y) => (
                <line key={y} x1="0" y1={y} x2={OUTFLOWS_CHART_WIDTH} y2={y} />
              ))}
            </g>
            {chart.columns.map((column) =>
              column.segments.map((segment) => (
                <rect
                  key={`${column.year}-${column.month}-${segment.key}`}
                  x={segment.x}
                  y={segment.y}
                  width={segment.width}
                  height={segment.height}
                  fill={seriesByKey[segment.key].colour}
                />
              )),
            )}
            <line
              x1="0"
              y1={OUTFLOWS_CHART_HEIGHT}
              x2={OUTFLOWS_CHART_WIDTH}
              y2={OUTFLOWS_CHART_HEIGHT}
              stroke="var(--color-neutral-400)"
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
            />
          </svg>

          {/* HTML overlays rather than SVG text: the SVG is scaled
              non-uniformly, which would stretch the glyphs. */}
          {chart.columns.map((column) =>
            column.segments
              .filter((segment) => segment.labelled)
              .map((segment) => (
                <span
                  key={`${column.year}-${column.month}-${segment.key}`}
                  data-testid="outflows-columns-pct"
                  className="outflows-cols__pct numeric"
                  title={`${seriesByKey[segment.key].label} ${money(segment.amount)}`}
                  style={{
                    left: `${(column.centreX / OUTFLOWS_CHART_WIDTH) * 100}%`,
                    top: `${(segment.centreY / OUTFLOWS_CHART_HEIGHT) * 100}%`,
                  }}
                >
                  {Math.round(segment.share * 100)}%
                </span>
              )),
          )}
        </div>

        <div />
        <div className="mbe__xaxis" data-testid="outflows-columns-xaxis">
          {months.map((m) => (
            <span key={`${m.year}-${m.month}`}>{MONTH_LABELS_SHORT[m.month - 1]}</span>
          ))}
        </div>
      </div>
    </section>
  );
}
