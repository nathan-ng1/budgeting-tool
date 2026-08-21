import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import IncomeVsExpensesByMonth from "./IncomeVsExpensesByMonth.jsx";

function month(overrides) {
  return { year: 2026, month: 7, income: 0, expenses: 0, net_balance: 0, transferred: 0, ...overrides };
}

function twelveMonths(overrides = {}) {
  return Array.from({ length: 12 }, (_, index) => {
    const monthIndex = ((7 - 1 + index) % 12) + 1;
    const year = monthIndex >= 7 ? 2026 : 2027;
    return month({ year, month: monthIndex, ...(overrides[index] ?? {}) });
  });
}

describe("IncomeVsExpensesByMonth", () => {
  it("labels the x-axis with every month of the Financial Year, in order", () => {
    render(<IncomeVsExpensesByMonth months={twelveMonths()} />);

    const labels = screen.getByText("Jul").parentElement;
    expect(labels.textContent).toBe("JulAugSepOctNovDecJanFebMarAprMayJun");
  });

  it("draws an Income bar and an Expenses bar for every month", () => {
    const { container } = render(
      <IncomeVsExpensesByMonth months={twelveMonths({ 0: { income: 5240, expenses: 3810 } })} />,
    );

    const incomeBars = container.querySelectorAll('g[fill="var(--color-accent-2-500)"] rect');
    const expenseBars = container.querySelectorAll('g[fill="var(--color-accent-600)"] rect');
    expect(incomeBars).toHaveLength(12);
    expect(expenseBars).toHaveLength(12);
  });

  it("renders a month with no Income or Expenses as a zero-height bar, not an omitted one", () => {
    const { container } = render(
      <IncomeVsExpensesByMonth months={twelveMonths({ 0: { income: 5240, expenses: 3810 } })} />,
    );

    const incomeBars = container.querySelectorAll('g[fill="var(--color-accent-2-500)"] rect');
    // Month index 1 (August) was never overridden, so it stays zeroed.
    expect(incomeBars[1].getAttribute("height")).toBe("0");
  });

  it("plots a Net line across the months", () => {
    const { container } = render(<IncomeVsExpensesByMonth months={twelveMonths()} />);

    expect(container.querySelector("path[stroke='var(--color-neutral-700)']")).toBeInTheDocument();
  });

  it("shows a legend for Income, Expenses, and Net", () => {
    render(<IncomeVsExpensesByMonth months={twelveMonths()} />);

    expect(screen.getByText("Income")).toBeInTheDocument();
    expect(screen.getByText("Expenses")).toBeInTheDocument();
    expect(screen.getByText("Net")).toBeInTheDocument();
  });
});
