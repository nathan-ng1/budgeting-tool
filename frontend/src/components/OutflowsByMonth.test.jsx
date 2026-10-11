import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SettingsProvider } from "../lib/settings.jsx";
import OutflowsByMonth from "./OutflowsByMonth.jsx";

function month(monthNumber, expenses = 0, billsSubscriptions = 0, debt = 0) {
  return {
    year: monthNumber >= 7 ? 2026 : 2027,
    month: monthNumber,
    income: 0,
    expenses,
    bills_subscriptions: billsSubscriptions,
    debt,
    available_to_save: 0,
    saved: 0,
  };
}

// July and August elapsed; the rest zeroed. Both months total 1,000, so the
// axis tops out at 1,000 and a segment is its amount x 0.24 pixels tall.
function twoElapsedMonths() {
  return [
    month(7, 600, 300, 100),
    month(8, 960, 20, 20),
    ...[9, 10, 11, 12, 1, 2, 3, 4, 5, 6].map((m) => month(m)),
  ];
}

describe("OutflowsByMonth", () => {
  it("shows each tall segment's share of its month's Outflows inside it", () => {
    render(<OutflowsByMonth months={twoElapsedMonths()} />);

    const labels = screen.getAllByTestId("outflows-columns-pct").map((el) => el.textContent);
    expect(labels).toContain("60%");
    expect(labels).toContain("30%");
    expect(labels).toContain("10%");
    expect(labels).toContain("96%");
  });

  it("omits the percentage where a segment is shorter than about 16px", () => {
    render(<OutflowsByMonth months={twoElapsedMonths()} />);

    // August's Bills & Subscriptions and Debt segments are 2% = 4.8px tall.
    const labels = screen.getAllByTestId("outflows-columns-pct").map((el) => el.textContent);
    expect(labels).not.toContain("2%");
    expect(labels).toHaveLength(4);
  });

  it("puts the Type and amount on a segment's hover title", () => {
    render(<OutflowsByMonth months={twoElapsedMonths()} />);

    expect(screen.getByTitle("Bills & Subscriptions $300")).toHaveTextContent("30%");
  });

  it("shows each Type with its year-to-date share and no dollar amounts in the legend", () => {
    render(<OutflowsByMonth months={twoElapsedMonths()} />);

    const legend = screen.getByTestId("outflows-columns-legend");
    expect(legend).toHaveTextContent("Expenses 78.0%");
    expect(legend).toHaveTextContent("Bills & Subscriptions 16.0%");
    expect(legend).toHaveTextContent("Debt 6.0%");
    expect(legend.textContent).not.toMatch(/[$££]/);
  });

  it("draws a labelled slot for every month, with unelapsed months empty", () => {
    render(<OutflowsByMonth months={twoElapsedMonths()} />);

    expect(screen.getByRole("heading", { name: "Outflows breakdown" })).toBeInTheDocument();
    const axis = screen.getByTestId("outflows-columns-xaxis");
    expect(within(axis).getAllByText(/^[A-Z][a-z]{2}$/)).toHaveLength(12);
    expect(screen.getByRole("img", { name: /Outflows by Type for every month/ })).toBeInTheDocument();
  });

  it("uses the Display Currency for the axis and hover amounts", () => {
    render(
      <SettingsProvider settings={{ currency: "GBP", financial_year_start_month: 7, date_order: "day-first" }}>
        <OutflowsByMonth months={twoElapsedMonths()} />
      </SettingsProvider>,
    );

    expect(screen.getByTitle("Bills & Subscriptions £300")).toBeInTheDocument();
    expect(screen.getByText("£1,000")).toBeInTheDocument();
  });

  it("says so, instead of drawing an empty chart, when the year has no Outflows", () => {
    render(<OutflowsByMonth months={[7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6].map((m) => month(m))} />);

    expect(screen.getByRole("heading", { name: "Outflows breakdown" })).toBeInTheDocument();
    expect(screen.getByText("No outflows recorded for this period.")).toBeInTheDocument();
    expect(screen.queryByRole("img")).toBeNull();
  });
});
