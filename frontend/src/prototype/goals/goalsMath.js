// PROTOTYPE (issue #209) - throwaway. Pure maths for the Goals design settled in
// map #207: status, pace, required-per-month, original plan, and the split tool's
// cent allocation. Nothing here touches the backend.

const pad = (n) => String(n).padStart(2, "0");

export const toISO = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

export function fromISO(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export const todayISO = () => toISO(new Date());

export function addMonthsISO(iso, n) {
  const d = fromISO(iso);
  const day = d.getDate();
  d.setDate(1);
  d.setMonth(d.getMonth() + n);
  const last = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
  d.setDate(Math.min(day, last));
  return toISO(d);
}

const dayDiff = (a, b) => Math.round((fromISO(b) - fromISO(a)) / 86400000);

// Inclusive calendar months, min 1 (decision Q20): 14 Oct -> 15 Dec = Oct, Nov, Dec = 3.
export function monthsInclusive(fromIso, toIso) {
  const a = fromISO(fromIso);
  const b = fromISO(toIso);
  return Math.max(1, (b.getFullYear() - a.getFullYear()) * 12 + b.getMonth() - a.getMonth() + 1);
}

export function savedFor(goalId, contributions) {
  return contributions.filter((c) => c.goalId === goalId).reduce((sum, c) => sum + c.amount, 0);
}

// Everything a variant needs to draw one Goal.
export function describeGoal(goal, contributions, today = todayISO()) {
  const saved = savedFor(goal.id, contributions);
  const { target, start, end } = goal;
  const achieved = saved >= target;

  let status = "Active";
  if (achieved) status = "Achieved";
  else if (today > end) status = "Ended";
  else if (today < start) status = "Upcoming";

  const totalDays = Math.max(1, dayDiff(start, end));
  const elapsed = Math.min(Math.max(dayDiff(start, today), 0), totalDays);
  const paceFraction = elapsed / totalDays;
  const paceAmount = target * paceFraction;
  const onTrack = saved >= paceAmount - 0.005;

  const monthsLeft = today > end ? 0 : monthsInclusive(today, end);
  const remaining = Math.max(target - saved, 0);

  return {
    goal,
    saved,
    remaining,
    status,
    fraction: Math.min(saved / target, 1),
    over: Math.max(saved - target, 0),
    paceFraction,
    paceAmount,
    onTrack,
    monthsLeft,
    requiredPerMonth: monthsLeft > 0 && !achieved ? remaining / monthsLeft : null,
    originalPlan: target / monthsInclusive(start, end),
    // "Behind" only means something while the Goal is live.
    flag: status === "Active" ? (onTrack ? "On track" : "Behind") : status === "Upcoming" ? "Upcoming" : status,
  };
}

const ORDER = { Active: 0, Upcoming: 1, Achieved: 2, Ended: 3 };
export const byStatus = (a, b) => ORDER[a.status] - ORDER[b.status] || a.goal.end.localeCompare(b.goal.end);

// Split tool (decision Q14): rows sum exactly to the total, no drift - largest remainder on cents.
// `rows` = [{ key, pct }]; whatever is left of 100% lands on the "rest" entry.
export function splitCents(total, rows) {
  const totalCents = Math.round(total * 100);
  const used = rows.reduce((s, r) => s + r.pct, 0);
  const entries = [...rows, { key: "__rest", pct: Math.max(100 - used, 0) }];
  const exact = entries.map((e) => ({ key: e.key, raw: (totalCents * e.pct) / 100 }));
  const floors = exact.map((e) => ({ key: e.key, cents: Math.floor(e.raw + 1e-9), frac: e.raw - Math.floor(e.raw + 1e-9) }));
  let leftover = totalCents - floors.reduce((s, f) => s + f.cents, 0);
  [...floors]
    .sort((a, b) => b.frac - a.frac)
    .forEach((f) => {
      if (leftover > 0) {
        f.cents += 1;
        leftover -= 1;
      }
    });
  return Object.fromEntries(floors.map((f) => [f.key, f.cents / 100]));
}

// Title uniqueness across all Goals incl. Past (decision Q15): trimmed, case-insensitive.
export function titleError(goals, title, exceptId = null) {
  const t = title.trim().toLowerCase();
  if (!t) return "Give the Goal a title.";
  if (goals.some((g) => g.id !== exceptId && g.title.trim().toLowerCase() === t)) {
    return "Another Goal already uses that title (Past goals count too). Pick a different name.";
  }
  return null;
}

export function fmtDate(iso) {
  return fromISO(iso).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
}
