// Geometry for the "Where did my income go?" bar.
//
// The endpoint already expresses each slice as a percentage of Income. The only
// thing decided here is the axis: when outflows exceed income the bar has to run
// past 100%, so the scale stretches and the 100%-of-income marker moves in from
// the right edge (the mockup's behaviour for an overspent month).

const TICK_STEP = 25;

const SEGMENT_ORDER = [
  { key: "expenses", label: "Expenses", amountField: "expenses_amount", pctField: "expenses_pct" },
  { key: "debt", label: "Debt", amountField: "debt_amount", pctField: "debt_pct" },
  { key: "saved", label: "Saved", amountField: "saved_amount", pctField: "saved_pct" },
  { key: "remaining", label: "Remaining", amountField: "remaining_amount", pctField: "remaining_pct" },
  { key: "over_income", label: "Over income", amountField: "over_income_amount", pctField: "over_income_pct" },
];

export function allocationBar(incomeAllocation) {
  const outflowPct = incomeAllocation.expenses_pct + incomeAllocation.debt_pct + incomeAllocation.saved_pct;
  const axisMax = Math.max(100, Math.ceil(outflowPct / 10) * 10);

  // over_income_pct is the tail of the outflow that runs past 100% of income -
  // it's already counted inside expenses_pct/debt_pct/saved_pct, not
  // stacked on top of them. Trim it back out of whichever segment(s) carry it -
  // Saved's slice first, since it's drawn immediately before Over income,
  // then Debt, then Expenses - so the segment widths sum to the real outflow
  // instead of double-counting the overage in the bar.
  let trim = incomeAllocation.over_income_pct;
  const displayPct = {};
  for (const key of ["saved", "debt", "expenses"]) {
    const raw = incomeAllocation[SEGMENT_ORDER.find((s) => s.key === key).pctField];
    displayPct[key] = Math.max(raw - trim, 0);
    trim = Math.max(trim - raw, 0);
  }

  const segments = SEGMENT_ORDER.filter((segment) => incomeAllocation[segment.pctField] > 0).map((segment) => ({
    key: segment.key,
    label: segment.label,
    amount: incomeAllocation[segment.amountField],
    pct: incomeAllocation[segment.pctField],
    width: `${((displayPct[segment.key] ?? incomeAllocation[segment.pctField]) / axisMax) * 100}%`,
  }));

  return {
    axisMax,
    segments,
    incomeMarkerLeft: `${(100 / axisMax) * 100}%`,
    ticks: ticksUpTo(axisMax),
  };
}

function ticksUpTo(axisMax) {
  const values = [];
  for (let tick = 0; tick <= axisMax; tick += TICK_STEP) {
    values.push(tick);
  }
  if (values[values.length - 1] !== axisMax) {
    values.push(axisMax);
  }
  return values.map((tick) => ({ label: `${tick}%`, left: `${(tick / axisMax) * 100}%` }));
}
