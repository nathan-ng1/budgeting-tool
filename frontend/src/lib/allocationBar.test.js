import { describe, expect, it } from "vitest";

import { allocationBar } from "./allocationBar.js";

function allocation(overrides = {}) {
  return {
    expenses_amount: 0,
    expenses_pct: 0,
    debt_amount: 0,
    debt_pct: 0,
    saved_amount: 0,
    saved_pct: 0,
    remaining_amount: 0,
    remaining_pct: 0,
    over_income_amount: 0,
    over_income_pct: 0,
    ...overrides,
  };
}

describe("allocationBar", () => {
  it("scales to 100% of income when the month stayed within income", () => {
    const bar = allocationBar(allocation({ expenses_pct: 70, saved_pct: 17.2, remaining_pct: 12.8 }));

    expect(bar.axisMax).toBe(100);
    expect(bar.incomeMarkerLeft).toBe("100%");
    expect(bar.ticks.map((tick) => tick.label)).toEqual(["0%", "25%", "50%", "75%", "100%"]);
  });

  it("widths are shares of the axis, so they read straight off the tick scale", () => {
    const bar = allocationBar(allocation({ expenses_pct: 70, saved_pct: 17.2, remaining_pct: 12.8 }));
    const widths = Object.fromEntries(bar.segments.map((segment) => [segment.key, segment.width]));

    expect(widths.expenses).toBe("70%");
    expect(widths.saved).toBe("17.2%");
    expect(widths.remaining).toBe("12.8%");
  });

  it("stretches the axis past 100% when outflows exceeded income, moving the income marker in", () => {
    const bar = allocationBar(allocation({ expenses_pct: 106.9, saved_pct: 17.2, over_income_pct: 24.1 }));

    // Outflows are 124.1% of income, so the axis runs to the next 10%.
    expect(bar.axisMax).toBe(130);
    expect(bar.incomeMarkerLeft).toBe(`${(100 / 130) * 100}%`);
    expect(bar.ticks[bar.ticks.length - 1].label).toBe("130%");
  });

  it("trims Over income back out of Expenses so the bar doesn't double-count the overage", () => {
    // expenses_pct (103.1%) already includes the amount that ran past income;
    // over_income_pct (3.1%) is that same tail, not additional outflow.
    const bar = allocationBar(allocation({ expenses_pct: 103.1, over_income_pct: 3.1 }));
    const widths = Object.fromEntries(bar.segments.map((segment) => [segment.key, segment.width]));

    expect(widths.expenses).toBe(`${(100 / 110) * 100}%`);
    expect(widths.over_income).toBe(`${(3.1 / 110) * 100}%`);
  });

  it("draws a Debt segment ordered between Expenses and Saved", () => {
    const bar = allocationBar(allocation({ expenses_pct: 40, debt_pct: 15, saved_pct: 10, remaining_pct: 35 }));
    const keys = bar.segments.map((segment) => segment.key);

    expect(keys).toEqual(["expenses", "debt", "saved", "remaining"]);
    expect(Object.fromEntries(bar.segments.map((s) => [s.key, s.width])).debt).toBe("15%");
  });

  it("trims Over income out of Saved then Debt then Expenses in that order", () => {
    // Outflows are 100% expenses + 20% debt + 10% saved = 130%, so
    // over_income_pct (30%) must come back out of Saved (10) then Debt
    // (20 remaining after Saved's 10) before touching Expenses at all.
    const bar = allocationBar(allocation({ expenses_pct: 100, debt_pct: 20, saved_pct: 10, over_income_pct: 30 }));
    const widths = Object.fromEntries(bar.segments.map((segment) => [segment.key, segment.width]));

    expect(widths.saved).toBe("0%");
    expect(widths.debt).toBe("0%");
    expect(widths.expenses).toBe(`${(100 / 130) * 100}%`);
    expect(widths.over_income).toBe(`${(30 / 130) * 100}%`);
  });

  it("drops the Remaining segment when there is nothing left over", () => {
    const bar = allocationBar(allocation({ expenses_pct: 106.9, over_income_pct: 6.9 }));
    const keys = bar.segments.map((segment) => segment.key);

    expect(keys).toContain("over_income");
    expect(keys).not.toContain("remaining");
  });

  it("has no segments to draw when there were no income-relative shares, rather than dividing by zero", () => {
    // IncomeAllocation renders its own copy for this case rather than an empty
    // bar - see the `income <= 0` branch there.
    const bar = allocationBar(allocation({ expenses_amount: 120 }));

    expect(bar.axisMax).toBe(100);
    expect(bar.segments).toEqual([]);
    expect(bar.incomeMarkerLeft).toBe("100%");
  });
});
