import { describe, expect, it } from "vitest";

import { CIRCUMFERENCE, cumulativeChart, donutSegments } from "./charts.js";

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
