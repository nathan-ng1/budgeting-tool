import { useEffect, useRef, useState } from "react";

import { useDateFormat, useMoney } from "../lib/settings.jsx";

const HEIGHT = 340;
const MARGIN = { left: 76, right: 112, top: 34, bottom: 58 };
const MIN_WIDTH = 420;
const DAY_MS = 86400000;

const day = (iso) => Date.parse(`${iso}T00:00:00Z`);

// Round-number steps from 0 up to just past the largest value.
export function niceTicks(max) {
  const raw = max / 4;
  const pow = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * pow).find((s) => s >= raw);
  const ticks = [];
  for (let value = 0; value <= max + step * 0.999; value += step) {
    ticks.push(Math.round(value * 100) / 100);
  }
  const top = ticks.findIndex((tick) => tick >= max);
  return top === -1 ? ticks : ticks.slice(0, top + 1);
}

// The first day of every month strictly inside (start, end), as ISO dates.
export function monthStarts(start, end) {
  const starts = [];
  const cursor = new Date(day(start));
  cursor.setUTCDate(1);
  cursor.setUTCMonth(cursor.getUTCMonth() + 1);
  while (cursor.toISOString().slice(0, 10) < end) {
    starts.push(cursor.toISOString().slice(0, 10));
    cursor.setUTCMonth(cursor.getUTCMonth() + 1);
  }
  return starts;
}

function useWidth(ref) {
  const [width, setWidth] = useState(760);
  useEffect(() => {
    const element = ref.current;
    if (!element) {
      return undefined;
    }
    const measure = (value) => (value > 0 ? setWidth(Math.max(MIN_WIDTH, Math.floor(value))) : undefined);
    measure(element.clientWidth);
    if (typeof ResizeObserver === "undefined") {
      return undefined;
    }
    const observer = new ResizeObserver(([entry]) => measure(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref]);
  return width;
}

// The dot-to-dot trajectory (Goals spec section 10): a marked point per
// Contribution at the running total, joined by straight lines and carried flat
// to today, against the Target and the Even pace line. Drawn at the container's
// real pixel width so its text matches the rest of the UI.
export default function GoalTrajectory({ goal, today }) {
  const { money } = useMoney();
  const { dayMonthYear } = useDateFormat();
  const wrap = useRef(null);
  const width = useWidth(wrap);

  const { start_date: start, end_date: end, target_amount: target, contributions } = goal;
  const plotW = width - MARGIN.left - MARGIN.right;
  const plotH = HEIGHT - MARGIN.top - MARGIN.bottom;
  const span = Math.max(1, (day(end) - day(start)) / DAY_MS);

  const saved = contributions.reduce((sum, c) => sum + c.amount, 0);
  const yTicks = niceTicks(Math.max(target, saved));
  const yMax = yTicks[yTicks.length - 1];
  const x = (iso) => MARGIN.left + (Math.min(Math.max((day(iso) - day(start)) / DAY_MS, 0), span) / span) * plotW;
  const y = (value) => MARGIN.top + (1 - Math.min(value / yMax, 1)) * plotH;

  // Starts from zero unless the first Contribution lands on the start date
  // itself, which would otherwise draw a vertical jump.
  let running = 0;
  const points = contributions.length > 0 && contributions[0].date <= start ? [] : [{ date: start, total: 0 }];
  const dots = contributions.map((c) => {
    running += c.amount;
    const point = { date: c.date, total: running };
    points.push(point);
    return point;
  });
  const showToday = today >= start && today <= end;
  const lastX = x(today < start ? start : showToday ? today : end);
  const line = [...points.map((p) => `${x(p.date)},${y(p.total)}`), `${lastX},${y(running)}`].join(" ");

  const months = monthStarts(start, end);
  const every = Math.ceil(months.length / Math.max(1, Math.floor(plotW / 62)));
  const xTicks = months
    .filter((_, index) => index % every === 0)
    .filter((iso) => x(iso) - MARGIN.left > 46 && MARGIN.left + plotW - x(iso) > 46);

  const tone = goal.flag === "Behind" || goal.status === "Ended" ? "var(--color-negative)" : "var(--color-positive)";
  const muted = "var(--color-neutral-600)";
  const grid = "var(--color-neutral-200)";
  const text = { fontFamily: "var(--font-body)", fontSize: 12 };

  // "Even pace" is written along the dashed line, a little above it.
  const [px1, py1, px2, py2] = [x(start), y(0), x(end), y(target)];
  const angle = (Math.atan2(py2 - py1, px2 - px1) * 180) / Math.PI;
  const labelX = px1 + (px2 - px1) * 0.62;
  const labelY = py1 + (py2 - py1) * 0.62 - 9;

  return (
    <div ref={wrap} className="goals__chart">
      <svg width={width} height={HEIGHT} role="img" aria-label={`Saved against even pace for ${goal.title}`} style={text}>
        {yTicks.map((value) => (
          <g key={value}>
            <line x1={MARGIN.left} x2={MARGIN.left + plotW} y1={y(value)} y2={y(value)} stroke={grid} />
            <text x={MARGIN.left - 10} y={y(value)} dy="0.32em" textAnchor="end" fill={muted} style={text}>
              {money(value)}
            </text>
          </g>
        ))}
        {xTicks.map((iso) => {
          const month = new Date(day(iso));
          const label = month.toLocaleDateString("en-AU", {
            month: "short",
            timeZone: "UTC",
            ...(month.getUTCMonth() === 0 ? { year: "numeric" } : {}),
          });
          return (
            <g key={iso}>
              <line x1={x(iso)} x2={x(iso)} y1={MARGIN.top} y2={MARGIN.top + plotH} stroke={grid} />
              <text x={x(iso)} y={MARGIN.top + plotH + 18} textAnchor="middle" fill={muted} style={text}>
                {label}
              </text>
            </g>
          );
        })}

        <line x1={MARGIN.left} x2={MARGIN.left + plotW} y1={MARGIN.top + plotH} y2={MARGIN.top + plotH} stroke="var(--color-neutral-400)" />
        <line x1={MARGIN.left} x2={MARGIN.left} y1={MARGIN.top} y2={MARGIN.top + plotH} stroke="var(--color-neutral-400)" />
        <text x={MARGIN.left} y={MARGIN.top + plotH + 36} textAnchor="start" fill={muted} style={text}>
          {dayMonthYear(start)}
        </text>
        <text x={MARGIN.left + plotW} y={MARGIN.top + plotH + 36} textAnchor="end" fill={muted} style={text}>
          {dayMonthYear(end)}
        </text>
        <text x={MARGIN.left + plotW / 2} y={HEIGHT - 6} textAnchor="middle" fill={muted} style={{ ...text, fontWeight: 600 }}>
          Date
        </text>
        <text
          transform={`translate(14 ${MARGIN.top + plotH / 2}) rotate(-90)`}
          textAnchor="middle"
          fill={muted}
          style={{ ...text, fontWeight: 600 }}
        >
          Amount saved
        </text>

        <line x1={MARGIN.left} x2={MARGIN.left + plotW} y1={y(target)} y2={y(target)} stroke="var(--color-neutral-500)" strokeDasharray="2 4" />
        <text x={MARGIN.left + plotW + 8} y={y(target)} dy="0.32em" fill="var(--color-text)" style={{ ...text, fontWeight: 600 }}>
          {`Target ${money(target)}`}
        </text>

        <line x1={px1} y1={py1} x2={px2} y2={py2} stroke="var(--color-neutral-500)" strokeDasharray="6 4" />
        <text x={labelX} y={labelY} textAnchor="middle" transform={`rotate(${angle} ${labelX} ${labelY})`} fill={muted} style={text}>
          Even pace
        </text>

        <polyline data-saved-line points={line} fill="none" stroke={tone} strokeWidth="2.5" />
        {dots.map((point, index) => (
          <circle
            key={index}
            data-contribution-point
            cx={x(point.date)}
            cy={y(point.total)}
            r="3.5"
            fill="var(--color-card)"
            stroke={tone}
            strokeWidth="2"
          />
        ))}
        <circle cx={lastX} cy={y(running)} r="4.5" fill={tone} />
        <text x={lastX + 10} y={y(running)} dy="0.32em" fill={tone} style={{ ...text, fontWeight: 600 }}>
          {`Saved ${money(running)}`}
        </text>

        {showToday && (
          <g>
            <line x1={x(today)} x2={x(today)} y1={MARGIN.top - 6} y2={MARGIN.top + plotH} stroke="var(--color-accent)" strokeWidth="1.5" />
            <text x={x(today)} y={MARGIN.top - 12} textAnchor="middle" fill="var(--color-accent)" style={{ ...text, fontWeight: 600 }}>
              Today
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}
