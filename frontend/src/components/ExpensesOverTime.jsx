import { CHART_HEIGHT, CHART_WIDTH, cumulativeChart } from "../lib/charts.js";
import { dayMonth, money } from "../lib/format.js";

const GRIDLINES = [0, 60, 120, 180];
const X_LABEL_STRIDE = 7;

export default function ExpensesOverTime({ overTime }) {
  const chart = cumulativeChart(overTime.daily);
  const lastPoint = chart.points[chart.points.length - 1];

  return (
    <section className="card card--chart">
      <div className="card__head">
        <h3>Expenses over time</h3>
        <div className="card__aside">
          <div className="card__aside-figure numeric">{money(overTime.total)}</div>
          <div className="card__aside-label numeric">{money(overTime.daily_average)} / day average</div>
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
          <svg viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`} preserveAspectRatio="none" role="img"
            aria-label={`Cumulative expenses across the month, ${money(overTime.total)} by month end`}>
            <defs>
              <linearGradient id="spendFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-accent-600)" stopOpacity="0.26" />
                <stop offset="100%" stopColor="var(--color-accent-600)" stopOpacity="0.03" />
              </linearGradient>
            </defs>
            <g stroke="var(--color-neutral-300)" strokeWidth="1" vectorEffect="non-scaling-stroke">
              {GRIDLINES.map((y) => (
                <line key={y} x1="0" y1={y} x2={CHART_WIDTH} y2={y} />
              ))}
            </g>
            <line
              x1="0"
              y1={CHART_HEIGHT}
              x2={CHART_WIDTH}
              y2={CHART_HEIGHT}
              stroke="var(--color-neutral-400)"
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
            />
            {chart.linePath !== "" && (
              <>
                <path d={chart.areaPath} fill="url(#spendFill)" />
                <path
                  d={chart.linePath}
                  fill="none"
                  stroke="var(--color-accent-600)"
                  strokeWidth="2.25"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                />
              </>
            )}
          </svg>
          {lastPoint !== undefined && (
            <span
              className="timechart__marker"
              style={{ left: "100%", top: `${(lastPoint.y / CHART_HEIGHT) * 100}%` }}
            />
          )}
        </div>

        <div />
        <div className="timechart__xaxis">
          {overTime.daily
            .map((day, index) => ({ day, index }))
            .filter(({ index }) => index % X_LABEL_STRIDE === 0)
            .map(({ day, index }) => (
              <span
                key={day.date}
                className="timechart__xlabel"
                style={{
                  left: `${(index / Math.max(overTime.daily.length - 1, 1)) * 100}%`,
                  transform: index === 0 ? "none" : "translateX(-50%)",
                }}
              >
                {dayMonth(day.date)}
              </span>
            ))}
        </div>
      </div>
    </section>
  );
}
