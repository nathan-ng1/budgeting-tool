import { describe, expect, it } from "vitest";

import { CIRCUMFERENCE, cumulativeChart, donutSegments, monthlyComparisonChart, plotGridlines } from "./charts.js";

describe("donutSegments", () => {
  it("lays each Category's arc end to end around the ring, largest first", () => {
    const segments = donutSegments([
      { category: "Groceries", amount: 750, pct_of_expenses: 75 },
      { category: "Transport", amount: 250, pct_of_expenses: 25 },
    ]);

    expect(segments).toHaveLength(2);
    expect(segments[0].length).toBeCloseTo(CIRCUMFERENCE * 0.75, 5);
    expect(segments[0].offset).toBe(-0);
    expect(segments[1].length).toBeCloseTo(CIRCUMFERENCE * 0.25, 5);
    // The second arc starts where the first one ended.
    expect(segments[1].offset).toBeCloseTo(-CIRCUMFERENCE * 0.75, 5);
  });

  it("carries each Category's own colour, not a rank-ordered one", () => {
    const [transport] = donutSegments([{ category: "Transport", amount: 10, pct_of_expenses: 100 }]);

    expect(transport.colour).toBe("#d67f48");
  });

  it("renders a month with no spending as no arcs at all", () => {
    expect(donutSegments([])).toEqual([]);
  });

  it("gives a negative-amount Category (e.g. Beem Adjustment, ADR-0015) a zero-length arc instead of a broken negative one, while still returning it for the legend", () => {
    const segments = donutSegments([
      { category: "Groceries", amount: 800, pct_of_expenses: 125 },
      { category: "Beem Adjustment", amount: -200, pct_of_expenses: -31.25 },
    ]);

    expect(segments).toHaveLength(2);
    // Groceries is the only real spend here, so it fills the whole ring -
    // the arc basis excludes the credit rather than dividing by the smaller
    // net total, which would overflow past a full circle.
    expect(segments[0].length).toBeCloseTo(CIRCUMFERENCE, 5);
    expect(segments[1].length).toBe(0);
    expect(segments[1].amount).toBe(-200);
  });
});

describe("cumulativeChart", () => {
  const daily = [
    { date: "2026-05-01", cumulative: 100 },
    { date: "2026-05-02", cumulative: 250 },
    { date: "2026-05-03", cumulative: 400 },
  ];

  it("spans the full width and puts the running total on an axis topped by a round number", () => {
    const chart = cumulativeChart(daily);

    expect(chart.axisMax).toBe(500);
    expect(chart.points[0]).toEqual({ x: 0, y: 240 - (100 / 500) * 240 });
    expect(chart.points[2].x).toBe(624);
  });

  it("builds a line path and a closed area path from the same points", () => {
    const chart = cumulativeChart(daily);

    expect(chart.linePath.startsWith("M0,")).toBe(true);
    expect(chart.linePath).not.toContain("Z");
    // The area is the line, dropped to the baseline and closed.
    expect(chart.areaPath.startsWith(chart.linePath)).toBe(true);
    expect(chart.areaPath.endsWith("Z")).toBe(true);
  });

  it("labels the y-axis from zero up to the axis maximum", () => {
    expect(cumulativeChart(daily).yTicks).toEqual([500, 375, 250, 125, 0]);
  });

  it("keeps a flat zero month on the baseline instead of dividing by zero", () => {
    const chart = cumulativeChart([
      { date: "2026-05-01", cumulative: 0 },
      { date: "2026-05-02", cumulative: 0 },
    ]);

    expect(chart.points.every((point) => point.y === 240)).toBe(true);
    expect(chart.axisMax).toBeGreaterThan(0);
  });

  it("has nothing to draw when the month has no days of data", () => {
    expect(cumulativeChart([]).points).toEqual([]);
    expect(cumulativeChart([]).linePath).toBe("");
  });
});

describe("monthlyComparisonChart", () => {
  const months = [
    { income: 1000, expenses: 600, debt: 300, net_balance: 400 },
    { income: 0, expenses: 0, debt: 0, net_balance: 0 },
  ];

  it("lays out each month's income, expense, and debt bars in its own slot, tallest against a round axis max", () => {
    const chart = monthlyComparisonChart(months);

    expect(chart.axisMax).toBe(1000);
    expect(chart.incomeBars[0]).toEqual({ x: 9, y: 0, width: 12, height: 240 });
    expect(chart.expenseBars[0]).toEqual({ x: 24, y: 96, width: 12, height: 144 });
    expect(chart.debtBars[0]).toEqual({ x: 39, y: 168, width: 12, height: 72 });
    // Second month's slot starts where the first one's 60-wide slot ends.
    expect(chart.incomeBars[1].x).toBe(69);
    expect(chart.expenseBars[1].x).toBe(84);
    expect(chart.debtBars[1].x).toBe(99);
  });

  it("plots the Net line through the centre of each month's slot", () => {
    const chart = monthlyComparisonChart(months);

    expect(chart.netPoints[0]).toEqual({ x: 30, y: 144 });
    expect(chart.netPoints[1]).toEqual({ x: 90, y: 240 });
    expect(chart.netLinePath).toBe("M30,144 L90,240");
  });

  it("renders a month with no Income, Expenses, or Debt as a zero-height bar, not an omitted one", () => {
    const chart = monthlyComparisonChart(months);

    expect(chart.incomeBars[1].height).toBe(0);
    expect(chart.expenseBars[1].height).toBe(0);
    expect(chart.debtBars[1].height).toBe(0);
  });

  it("has nothing to draw when there are no months", () => {
    const chart = monthlyComparisonChart([]);

    expect(chart.incomeBars).toEqual([]);
    expect(chart.expenseBars).toEqual([]);
    expect(chart.debtBars).toEqual([]);
    expect(chart.netPoints).toEqual([]);
    expect(chart.netLinePath).toBe("");
  });

  it("clamps a deficit month's Net point to the $0 baseline instead of letting it run off the chart", () => {
    const chart = monthlyComparisonChart([{ income: 400, expenses: 1000, debt: 0, net_balance: -600 }]);

    expect(chart.netPoints[0].y).toBe(240);
  });
});

describe("plotGridlines", () => {
  it("gives the four gridlines below the baseline, evenly spaced up from zero", () => {
    expect(plotGridlines(240)).toEqual([0, 60, 120, 180]);
  });
});
