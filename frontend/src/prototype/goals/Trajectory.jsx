// PROTOTYPE (issue #209) - throwaway. Saved-vs-even-pace chart. Drawn at the container's real
// pixel width (not a scaled viewBox) so its text is the same size and font as the rest of the UI.
import { useEffect, useRef, useState } from "react";

import { useMoney } from "../../lib/settings.jsx";
import { fmtDate, fromISO, toISO, todayISO } from "./goalsMath.js";

const HEIGHT = 340;
const M = { left: 76, right: 112, top: 34, bottom: 58 };
const FONT = { fontFamily: "var(--font-body)", fontSize: 12 };

function useWidth(ref) {
  const [width, setWidth] = useState(760);
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    setWidth(Math.max(420, Math.floor(el.clientWidth)));
    if (typeof ResizeObserver === "undefined") return undefined;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(420, Math.floor(entry.contentRect.width))));
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref]);
  return width;
}

// 4-6 round-number steps from 0 up to just past the largest value.
function niceTicks(max) {
  const raw = max / 4;
  const pow = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * pow).find((s) => s >= raw);
  const ticks = [];
  for (let v = 0; v <= max + step * 0.999; v += step) ticks.push(Math.round(v * 100) / 100);
  return ticks.slice(0, ticks.findIndex((t) => t >= max) + 1 || undefined);
}

// First day of every month strictly inside (start, end).
function monthStarts(start, end) {
  const out = [];
  const d = fromISO(start);
  d.setDate(1);
  d.setMonth(d.getMonth() + 1);
  while (toISO(d) < end) {
    out.push(toISO(d));
    d.setMonth(d.getMonth() + 1);
  }
  return out;
}

export default function Trajectory({ d, contributions }) {
  const { money } = useMoney();
  const wrap = useRef(null);
  const width = useWidth(wrap);
  const { start, end, target, id } = d.goal;

  const plotW = width - M.left - M.right;
  const plotH = HEIGHT - M.top - M.bottom;
  const span = Math.max(1, (fromISO(end) - fromISO(start)) / 86400000);
  const yTicks = niceTicks(Math.max(target, d.saved));
  const yMax = yTicks[yTicks.length - 1];
  const x = (iso) => M.left + (Math.min(Math.max((fromISO(iso) - fromISO(start)) / 86400000, 0), span) / span) * plotW;
  const y = (v) => M.top + (1 - Math.min(v / yMax, 1)) * plotH;

  const own = contributions.filter((c) => c.goalId === id).sort((a, b) => a.date.localeCompare(b.date));
  // Dot to dot: one marked point per contribution, at the running total on its date, joined by
  // straight lines, then carried flat to today. Starts from 0 unless the first contribution lands
  // on the start date itself (which would otherwise draw a vertical jump).
  let run = 0;
  const points = own.length > 0 && own[0].date <= start ? [] : [[start, 0]];
  own.forEach((c) => {
    run += c.amount;
    points.push([c.date, run]);
  });
  const today = todayISO();
  const showToday = today >= start && today <= end;
  const lastX = x(showToday ? today : end);
  const pts = [...points.map(([iso, v]) => `${x(iso)},${y(v)}`), `${lastX},${y(run)}`];

  const everyN = Math.ceil(monthStarts(start, end).length / Math.max(1, Math.floor(plotW / 62)));
  const xTicks = monthStarts(start, end)
    .filter((_, i) => i % everyN === 0)
    .filter((iso) => x(iso) - M.left > 46 && M.left + plotW - x(iso) > 46);

  const line = d.flag === "Behind" || d.status === "Ended" ? "var(--color-negative)" : "var(--color-positive)";
  const muted = "var(--color-neutral-600)";
  const grid = "var(--color-neutral-200)";

  // "Even pace" is written along the dashed line, a little above it.
  const px1 = x(start);
  const py1 = y(0);
  const px2 = x(end);
  const py2 = y(target);
  const angle = (Math.atan2(py2 - py1, px2 - px1) * 180) / Math.PI;
  const lx = px1 + (px2 - px1) * 0.62;
  const ly = py1 + (py2 - py1) * 0.62 - 9;

  return (
    <div ref={wrap} className="gp-chart-wrap">
      <svg width={width} height={HEIGHT} role="img" aria-label={`Saved against even pace for ${d.goal.title}`} style={FONT}>
        {yTicks.map((v) => (
          <g key={v}>
            <line x1={M.left} x2={M.left + plotW} y1={y(v)} y2={y(v)} stroke={grid} />
            <text x={M.left - 10} y={y(v)} dy="0.32em" textAnchor="end" fill={muted} style={FONT}>{money(v)}</text>
          </g>
        ))}
        {xTicks.map((iso) => {
          const m = fromISO(iso);
          const label = m.toLocaleDateString("en-AU", { month: "short", ...(m.getMonth() === 0 ? { year: "numeric" } : {}) });
          return (
            <g key={iso}>
              <line x1={x(iso)} x2={x(iso)} y1={M.top} y2={M.top + plotH} stroke={grid} />
              <text x={x(iso)} y={M.top + plotH + 18} textAnchor="middle" fill={muted} style={FONT}>{label}</text>
            </g>
          );
        })}

        <line x1={M.left} x2={M.left + plotW} y1={M.top + plotH} y2={M.top + plotH} stroke="var(--color-neutral-400)" />
        <line x1={M.left} x2={M.left} y1={M.top} y2={M.top + plotH} stroke="var(--color-neutral-400)" />
        <text x={M.left} y={M.top + plotH + 36} textAnchor="start" fill={muted} style={FONT}>{fmtDate(start)}</text>
        <text x={M.left + plotW} y={M.top + plotH + 36} textAnchor="end" fill={muted} style={FONT}>{fmtDate(end)}</text>
        <text x={M.left + plotW / 2} y={HEIGHT - 6} textAnchor="middle" fill={muted} style={{ ...FONT, fontWeight: 600 }}>Date</text>
        <text transform={`translate(14 ${M.top + plotH / 2}) rotate(-90)`} textAnchor="middle" fill={muted} style={{ ...FONT, fontWeight: 600 }}>Amount saved</text>

        {/* Target */}
        <line x1={M.left} x2={M.left + plotW} y1={y(target)} y2={y(target)} stroke="var(--color-neutral-500)" strokeDasharray="2 4" />
        <text x={M.left + plotW + 8} y={y(target)} dy="0.32em" fill="var(--color-text)" style={{ ...FONT, fontWeight: 600 }}>
          Target {money(target)}
        </text>

        {/* Even pace */}
        <line x1={px1} y1={py1} x2={px2} y2={py2} stroke="var(--color-neutral-500)" strokeDasharray="6 4" />
        <text x={lx} y={ly} textAnchor="middle" transform={`rotate(${angle} ${lx} ${ly})`} fill={muted} style={FONT}>Even pace</text>

        {/* Saved */}
        <polyline points={pts.join(" ")} fill="none" stroke={line} strokeWidth="2.5" />
        {points.filter(([, v]) => v > 0).map(([iso, v]) => (
          <circle key={iso} cx={x(iso)} cy={y(v)} r="3.5" fill="var(--color-card)" stroke={line} strokeWidth="2" />
        ))}
        <circle cx={lastX} cy={y(run)} r="4.5" fill={line} />
        <text x={lastX + 10} y={y(run)} dy="0.32em" fill={line} style={{ ...FONT, fontWeight: 600 }}>Saved {money(run)}</text>

        {/* Today */}
        {showToday && (
          <g>
            <line x1={x(today)} x2={x(today)} y1={M.top - 6} y2={M.top + plotH} stroke="var(--color-accent)" strokeWidth="1.5" />
            <text x={x(today)} y={M.top - 12} textAnchor="middle" fill="var(--color-accent)" style={{ ...FONT, fontWeight: 600 }}>Today</text>
          </g>
        )}
      </svg>
    </div>
  );
}
