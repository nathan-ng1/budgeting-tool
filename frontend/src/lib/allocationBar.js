// Geometry for the "Where did my income go?" bar.
//
// The endpoint already expresses each slice as a percentage of Income. The only
// thing decided here is the axis: when outflows exceed income the bar has to run
// past 100%, so the scale stretches and the 100%-of-income marker moves in from
// the right edge (the mockup's behaviour for an overspent month).

const TICK_STEP = 25;

const SEGMENT_ORDER = [
  { key: "expenses", label: "Expenses", amountField: "expenses_amount", pctField: "expenses_pct" },
  {
    key: "bills_subscriptions",
    label: "Bills & Subscriptions",
    amountField: "bills_subscriptions_amount",
    pctField: "bills_subscriptions_pct",
  },
  { key: "debt", label: "Debt", amountField: "debt_amount", pctField: "debt_pct" },
  { key: "saved", label: "Saved", amountField: "saved_amount", pctField: "saved_pct" },
  { key: "remaining", label: "Remaining", amountField: "remaining_amount", pctField: "remaining_pct" },
  { key: "over_income", label: "Over income", amountField: "over_income_amount", pctField: "over_income_pct" },
];

// The outflow segments (everything before Remaining), walked back from the
// one drawn nearest Over income - derived from SEGMENT_ORDER so the two can't
// drift apart when a Type is added.
const OUTFLOW_SEGMENTS_LAST_FIRST = SEGMENT_ORDER.slice(
  0,
  SEGMENT_ORDER.findIndex((s) => s.key === "remaining"),
).reverse();

export function allocationBar(incomeAllocation) {
  // Size the axis from Over income, not by summing the outflow shares: each
  // share is rounded to 1 dp independently, so an exactly balanced month can
  // sum to 100.1% and would otherwise draw a spurious 100-110% tail (#166).
  const axisMax = Math.max(100, Math.ceil((100 + incomeAllocation.over_income_pct) / 10) * 10);

  // over_income_pct is the tail of the outflow that runs past 100% of income -
  // it's already counted inside the outflow segments' own pcts, not stacked
  // on top of them. Trim it back out of whichever segment(s) carry it, walking
  // back from the one drawn immediately before Over income - Saved, then
  // Debt, then Bills & Subscriptions, then Expenses - so the segment widths
  // sum to the real outflow instead of double-counting the overage in the bar.
  let trim = incomeAllocation.over_income_pct;
  const displayPct = {};
  for (const { key, pctField } of OUTFLOW_SEGMENTS_LAST_FIRST) {
    const raw = incomeAllocation[pctField];
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
