import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import SpendingOverTime from "./SpendingOverTime.jsx";

const OVER_TIME = {
  daily: [
    { date: "2026-08-01", cumulative: 100 },
    { date: "2026-08-02", cumulative: 100 },
    { date: "2026-08-03", cumulative: 720 }, // a lumpy bill
  ],
  total: 720,
  daily_average: 23,
};

describe("SpendingOverTime", () => {
  it("is titled Spending and states the total and per-day average", () => {
    render(<SpendingOverTime overTime={OVER_TIME} />);

    expect(screen.getByRole("heading", { name: "Spending over time" })).toBeInTheDocument();
    expect(screen.getByText("$720", { selector: ".card__aside-figure" })).toBeInTheDocument();
    expect(screen.getByText("$23 / day average")).toBeInTheDocument();
  });

  it("describes the chart as cumulative spending", () => {
    render(<SpendingOverTime overTime={OVER_TIME} />);

    expect(
      screen.getByRole("img", { name: "Cumulative spending across the month, $720 by month end" }),
    ).toBeInTheDocument();
  });
});
