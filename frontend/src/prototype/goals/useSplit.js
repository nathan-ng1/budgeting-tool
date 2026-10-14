// PROTOTYPE (issue #209) - throwaway. Split-tool state shared by all variants so each
// can be judged on presentation only. Rules: Q14 (cap 100%, remainder row, exact cents,
// last-used percentages prefilled) and Q21 (total prefilled from the month's Unallocated).
import { useMemo, useState } from "react";

import { splitCents, todayISO } from "./goalsMath.js";
import { actions, useGoals } from "./store.js";

export default function useSplit(activeGoals) {
  const { lastPercents, unallocated } = useGoals();
  const [total, setTotal] = useState(unallocated > 0 ? String(unallocated) : "");
  const [date, setDate] = useState(todayISO());
  const [restCategory, setRestCategory] = useState("Savings");
  const [percents, setPercents] = useState(() =>
    Object.fromEntries(activeGoals.map((g) => [g.id, lastPercents[g.id] ?? 0])),
  );

  const used = activeGoals.reduce((s, g) => s + (Number(percents[g.id]) || 0), 0);
  const overCap = used > 100.0001;
  const restPct = Math.max(100 - used, 0);
  const totalNumber = Number(total) || 0;

  const preview = useMemo(() => {
    if (!(totalNumber > 0) || overCap) return null;
    const rows = activeGoals.map((g) => ({ key: g.id, pct: Number(percents[g.id]) || 0 })).filter((r) => r.pct > 0);
    const amounts = splitCents(totalNumber, rows);
    return {
      goals: rows.map((r) => ({ goal: activeGoals.find((g) => g.id === r.key), pct: r.pct, amount: amounts[r.key] })),
      rest: { pct: restPct, amount: amounts.__rest },
    };
  }, [activeGoals, percents, totalNumber, overCap, restPct]);

  return {
    total,
    setTotal,
    date,
    setDate,
    restCategory,
    setRestCategory,
    percents,
    percentOf: (goalId) => percents[goalId] ?? 0,
    setPercent: (goalId, value) => setPercents((p) => ({ ...p, [goalId]: value })),
    used,
    overCap,
    restPct,
    preview,
    unallocated,
    canApply: preview !== null && preview.goals.length > 0,
    apply() {
      actions.applySplit({
        total: totalNumber,
        date,
        percents: Object.fromEntries(activeGoals.map((g) => [g.id, Number(percents[g.id]) || 0])),
        restCategory,
      });
    },
  };
}
