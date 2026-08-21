import { MONTH_CHART_HEIGHT, MONTH_CHART_WIDTH, monthlyComparisonChart, plotGridlines } from "../lib/charts.js";
import { money } from "../lib/format.js";
import { MONTH_LABELS_SHORT } from "../lib/months.js";

export default function IncomeVsExpensesByMonth({ months }) {
  const chart = monthlyComparisonChart(months);
  const gridlines = plotGridlines(MONTH_CHART_HEIGHT);

  return (
    <section className="card card--chart">
      <div className="card__head">
        <h3>Income vs Expenses by month</h3>
        <div className="allocation__legend">
          <span className="allocation__legend-item">
            <span className="dot dot--lg" style={{ background: "var(--color-accent-2-500)" }} />
            Income
          </span>
          <span className="allocation__legend-item">
            <span className="dot dot--lg" style={{ background: "var(--color-accent-600)" }} />
            Expenses
          </span>
          <span className="allocation__legend-item">
            <span className="mbe__line-swatch" />
            Net
          </span>
        </div>
      </div>

      <div className="timechart">
        <div className="timechart__yaxis numeric">
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

        <div className="timechart__plot">
          <svg
            viewBox={`0 0 ${MONTH_CHART_WIDTH} ${MONTH_CHART_HEIGHT}`}
            preserveAspectRatio="none"
            role="img"
            aria-label="Income and Expenses for every month of the Financial Year, with a Net line"
          >
            <g stroke="var(--color-neutral-300)" strokeWidth="1" vectorEffect="non-scaling-stroke">
              {gridlines.map((y) => (
                <line key={y} x1="0" y1={y} x2={MONTH_CHART_WIDTH} y2={y} />
              ))}
            </g>
            <g fill="var(--color-accent-2-500)">
              {chart.incomeBars.map((bar, index) => (
                <rect key={index} x={bar.x} y={bar.y} width={bar.width} height={bar.height} rx="3" />
              ))}
            </g>
            <g fill="var(--color-accent-600)">
              {chart.expenseBars.map((bar, index) => (
                <rect key={index} x={bar.x} y={bar.y} width={bar.width} height={bar.height} rx="3" />
              ))}
            </g>
            {chart.netLinePath !== "" && (
              <g>
                <path
                  d={chart.netLinePath}
                  fill="none"
                  stroke="var(--color-neutral-700)"
                  strokeWidth="2"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                />
                <g fill="var(--color-card)" stroke="var(--color-neutral-700)" strokeWidth="1.75" vectorEffect="non-scaling-stroke">
                  {chart.netPoints.map((point, index) => (
                    <circle key={index} cx={point.x} cy={point.y} r="3.2" />
                  ))}
                </g>
              </g>
            )}
            <line
              x1="0"
              y1={MONTH_CHART_HEIGHT}
              x2={MONTH_CHART_WIDTH}
              y2={MONTH_CHART_HEIGHT}
              stroke="var(--color-neutral-400)"
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
        </div>

        <div />
        <div className="mbe__xaxis">
          {months.map((m) => (
            <span key={`${m.year}-${m.month}`}>{MONTH_LABELS_SHORT[m.month - 1]}</span>
          ))}
        </div>
      </div>
    </section>
  );
}
