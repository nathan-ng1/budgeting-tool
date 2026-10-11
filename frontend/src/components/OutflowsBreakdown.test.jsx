import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SettingsProvider } from "../lib/settings.jsx";
import OutflowsBreakdown from "./OutflowsBreakdown.jsx";

function tiles(overrides = {}) {
  return { income: 0, expenses: 0, bills_subscriptions: 0, debt: 0, saved: 0, ...overrides };
}

describe("OutflowsBreakdown", () => {
  it("draws one segment per Type, each sized to its share of Outflows", () => {
    render(<OutflowsBreakdown tiles={tiles({ expenses: 600, bills_subscriptions: 300, debt: 100 })} />);

    const segments = screen.getAllByTestId("outflows-segment");
    expect(segments.map((s) => s.style.width)).toEqual(["60%", "30%", "10%"]);
  });

  it("fills the whole bar whatever Income was, and has no Income marker", () => {
    const { container } = render(<OutflowsBreakdown tiles={tiles({ income: 100000, expenses: 50, debt: 50 })} />);

    const widths = screen.getAllByTestId("outflows-segment").map((s) => parseFloat(s.style.width));
    expect(widths.reduce((a, b) => a + b, 0)).toBeCloseTo(100);
    expect(container.querySelector(".allocation__marker")).toBeNull();
  });

  it("labels a 0 to 100% scale beneath the bar", () => {
    render(<OutflowsBreakdown tiles={tiles({ expenses: 10 })} />);

    for (const label of ["0%", "25%", "50%", "75%", "100%"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
  });

  it("shows the dollar amount inside wide segments only, keeping it on hover for narrow ones", () => {
    render(<OutflowsBreakdown tiles={tiles({ expenses: 900, bills_subscriptions: 60, debt: 40 })} />);

    const [expenses, bills, debt] = screen.getAllByTestId("outflows-segment");
    expect(expenses).toHaveTextContent("$900");
    expect(bills).toBeEmptyDOMElement();
    expect(debt).toBeEmptyDOMElement();
    expect(bills).toHaveAttribute("title", "Bills & Subscriptions $60");
    expect(debt).toHaveAttribute("title", "Debt $40");
  });

  it("puts each Type's name and percentage in the legend", () => {
    render(<OutflowsBreakdown tiles={tiles({ expenses: 600, bills_subscriptions: 300, debt: 100 })} />);

    const legend = screen.getByTestId("outflows-legend");
    expect(within(legend).getByText("Expenses")).toBeInTheDocument();
    expect(within(legend).getByText("60.0%")).toBeInTheDocument();
    expect(within(legend).getByText("Bills & Subscriptions")).toBeInTheDocument();
    expect(within(legend).getByText("30.0%")).toBeInTheDocument();
    expect(within(legend).getByText("Debt")).toBeInTheDocument();
    expect(within(legend).getByText("10.0%")).toBeInTheDocument();
  });

  it("uses the shared Type colours and leaves Savings out", () => {
    render(<OutflowsBreakdown tiles={tiles({ expenses: 1, bills_subscriptions: 1, debt: 1, saved: 500 })} />);

    const fills = screen.getAllByTestId("outflows-segment").map((s) => s.style.background);
    expect(fills).toEqual(["var(--color-negative-fill)", "var(--color-bills-subscriptions)", "var(--color-debt)"]);
    expect(screen.queryByText(/Saved|Savings/)).not.toBeInTheDocument();
  });

  it("says so when the month has no Outflows", () => {
    render(<OutflowsBreakdown tiles={tiles({ income: 5000, saved: 200 })} />);

    expect(screen.getByRole("heading", { name: "Outflows breakdown" })).toBeInTheDocument();
    expect(screen.getByText("No outflows recorded for this month.")).toBeInTheDocument();
    expect(screen.queryByTestId("outflows-segment")).not.toBeInTheDocument();
  });

  it("formats amounts in the Display Currency", () => {
    render(
      <SettingsProvider settings={{ currency: "GBP", financial_year_start_month: 7, date_order: "day-first" }}>
        <OutflowsBreakdown tiles={tiles({ expenses: 800, bills_subscriptions: 100, debt: 100 })} />
      </SettingsProvider>,
    );

    const [expenses, , debt] = screen.getAllByTestId("outflows-segment");
    expect(expenses).toHaveTextContent("£800");
    expect(debt).toHaveAttribute("title", "Debt £100");
  });
});
