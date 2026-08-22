// SVG geometry for the two Overview charts. Both take the Month Overview
// endpoint's numbers as given (Issue #27 owns the aggregation) and turn them
// into coordinates - no totalling or re-deriving happens here.

import { colourForCategory } from "./categoryColours.js";

// Donut: the mockup's ring is r=70 in a 200x200 viewBox, drawn with
// stroke-dasharray, so arc lengths are fractions of the circumference.
export const DONUT_RADIUS = 70;
export const CIRCUMFERENCE = 2 * Math.PI * DONUT_RADIUS;

// Line chart: the mockup's plot area, in its own viewBox units.
export const CHART_WIDTH = 624;
export const CHART_HEIGHT = 240;
const Y_TICK_COUNT = 4;

// The horizontal gridlines drawn inside a plot area of the given height - the
// same four fractions (0%/25%/50%/75%) both charts use; the 100% line is each
// chart's baseline, drawn separately since it carries a different stroke.
export function plotGridlines(height) {
  return yTicksUpTo(height)
    .slice(1)
    .reverse();
}

export function donutSegments(spendingByCategory) {
  let consumed = 0;

  return spendingByCategory.map(({ category, amount, pct_of_expenses: pct }) => {
    const length = (pct / 100) * CIRCUMFERENCE;
    const segment = {
      category,
      amount,
      length,
      // Each arc starts where the previous one ended; a negative dashoffset
      // rotates the arc forward around the ring.
      offset: -consumed,
      colour: colourForCategory(category),
    };
    consumed += length;
    return segment;
  });
}

// Income, Expenses & Debt by Month: the mockup's grouped-bar-plus-line plot
// area, sized for 12 equal month slots (Issue #41; Debt bar added by #50).
export const MONTH_CHART_WIDTH = 720;
export const MONTH_CHART_HEIGHT = 240;
const MONTH_SLOT_WIDTH = MONTH_CHART_WIDTH / 12;
const MONTH_BAR_WIDTH = 12;
const MONTH_BAR_GAP = 3;
// Three bars-plus-gaps centred within the month slot.
const MONTH_BARS_WIDTH = 3 * MONTH_BAR_WIDTH + 2 * MONTH_BAR_GAP;
const MONTH_INCOME_BAR_OFFSET = (MONTH_SLOT_WIDTH - MONTH_BARS_WIDTH) / 2;
const MONTH_EXPENSE_BAR_OFFSET = MONTH_INCOME_BAR_OFFSET + MONTH_BAR_WIDTH + MONTH_BAR_GAP;
const MONTH_DEBT_BAR_OFFSET = MONTH_EXPENSE_BAR_OFFSET + MONTH_BAR_WIDTH + MONTH_BAR_GAP;
const MONTH_LINE_OFFSET = MONTH_INCOME_BAR_OFFSET + MONTH_BARS_WIDTH / 2;

export function monthlyComparisonChart(monthlyTotals) {
  if (monthlyTotals.length === 0) {
    return { incomeBars: [], expenseBars: [], debtBars: [], netPoints: [], netLinePath: "", axisMax: 0, yTicks: [] };
  }

  const peak = Math.max(...monthlyTotals.map((m) => Math.max(m.income, m.expenses, m.debt)));
  const axisMax = roundedAxisMax(peak);
  const valueY = (value) => MONTH_CHART_HEIGHT - (value / axisMax) * MONTH_CHART_HEIGHT;

  const bar = (value, offset, index) => ({
    x: index * MONTH_SLOT_WIDTH + offset,
    y: round(valueY(value)),
    width: MONTH_BAR_WIDTH,
    height: round(MONTH_CHART_HEIGHT - valueY(value)),
  });

  const incomeBars = monthlyTotals.map((m, index) => bar(m.income, MONTH_INCOME_BAR_OFFSET, index));
  const expenseBars = monthlyTotals.map((m, index) => bar(m.expenses, MONTH_EXPENSE_BAR_OFFSET, index));
  const debtBars = monthlyTotals.map((m, index) => bar(m.debt, MONTH_DEBT_BAR_OFFSET, index));

  const netPoints = monthlyTotals.map((m, index) => ({
    x: index * MONTH_SLOT_WIDTH + MONTH_LINE_OFFSET,
    // A deficit month plots below the $0 baseline - clamped there rather
    // than left to run off the bottom of the viewBox, where it would be
    // silently clipped by the SVG's default overflow:hidden.
    y: round(Math.min(valueY(m.net_balance), MONTH_CHART_HEIGHT)),
  }));
  const netLinePath = netPoints.map((point, index) => `${index === 0 ? "M" : "L"}${point.x},${point.y}`).join(" ");

  return { incomeBars, expenseBars, debtBars, netPoints, netLinePath, axisMax, yTicks: yTicksUpTo(axisMax) };
}

export function cumulativeChart(daily) {
  if (daily.length === 0) {
    return { points: [], linePath: "", areaPath: "", axisMax: 0, yTicks: [] };
  }

  const peak = Math.max(...daily.map((day) => day.cumulative));
  const axisMax = roundedAxisMax(peak);

  const step = daily.length > 1 ? CHART_WIDTH / (daily.length - 1) : 0;
  const points = daily.map((day, index) => ({
    x: index * step,
    y: CHART_HEIGHT - (day.cumulative / axisMax) * CHART_HEIGHT,
  }));

  const linePath = points.map((point, index) => `${index === 0 ? "M" : "L"}${round(point.x)},${round(point.y)}`).join(" ");
  const last = points[points.length - 1];
  const areaPath = `${linePath} L${round(last.x)},${CHART_HEIGHT} L${round(points[0].x)},${CHART_HEIGHT} Z`;

  return { points, linePath, areaPath, axisMax, yTicks: yTicksUpTo(axisMax) };
}

function roundedAxisMax(peak) {
  if (peak <= 0) {
    // A month with no spending still needs a scale to draw an axis against;
    // without one every point would divide by zero.
    return 100;
  }

  // Round up to a 1/2/5 x power-of-ten step so the four gridlines land on
  // readable dollar figures rather than on fractions of the peak.
  const magnitude = 10 ** Math.floor(Math.log10(peak));
  const step = [1, 2, 2.5, 5, 10].find((multiple) => peak <= multiple * magnitude) * magnitude;
  return Math.ceil(peak / (step / Y_TICK_COUNT)) * (step / Y_TICK_COUNT);
}

function yTicksUpTo(axisMax) {
  return Array.from({ length: Y_TICK_COUNT + 1 }, (_, index) => axisMax - (index * axisMax) / Y_TICK_COUNT);
}

function round(value) {
  return Math.round(value * 100) / 100;
}
