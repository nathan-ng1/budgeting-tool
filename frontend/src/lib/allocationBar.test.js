import { describe, expect, it } from "vitest";

import { allocationBar } from "./allocationBar.js";

function allocation(overrides = {}) {
  return {
    expenses_amount: 0,
    expenses_pct: 0,
    transferred_amount: 0,
    transferred_pct: 0,
    remaining_amount: 0,
    remaining_pct: 0,
    over_income_amount: 0,
    over_income_pct: 0,
    ...overrides,
  };
}

describe("allocationBar", () => {
  it("scales to 100% of income when the month stayed within income", () => {
    const bar = allocationBar(allocation({ expenses_pct: 70, transferred_pct: 17.2, remaining_pct: 12.8 }));

    expect(bar.axisMax).toBe(100);
    expect(bar.incomeMarkerLeft).toBe("100%");
    expect(bar.ticks.map((tick) => tick.label)).toEqual(["0%", "25%", "50%", "75%", "100%"]);
  });

  it("widths are shares of the axis, so they read straight off the tick scale", () => {
    const bar = allocationBar(allocation({ expenses_pct: 70, transferred_pct: 17.2, remaining_pct: 12.8 }));
    const widths = Object.fromEntries(bar.segments.map((segment) => [segment.key, segment.width]));

    expect(widths.expenses).toBe("70%");
    expect(widths.transferred).toBe("17.2%");
    expect(widths.remaining).toBe("12.8%");
  });

  it("stretches the axis past 100% when outflows exceeded income, moving the income marker in", () => {
    const bar = allocationBar(allocation({ expenses_pct: 106.9, transferred_pct: 17.2, over_income_pct: 24.1 }));

    // Outflows are 124.1% of income, so the axis runs to the next 10%.
    expect(bar.axisMax).toBe(130);
    expect(bar.incomeMarkerLeft).toBe(`${(100 / 130) * 100}%`);
    expect(bar.ticks[bar.ticks.length - 1].label).toBe("130%");
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
