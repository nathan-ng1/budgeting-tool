import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import IncomeVsExpensesByMonth from "./IncomeVsExpensesByMonth.jsx";

function month(overrides) {
  return { year: 2026, month: 7, income: 0, expenses: 0, bills_subscriptions: 0, debt: 0, net_balance: 0, saved: 0, ...overrides };
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

  it("draws an Income bar, an Expenses bar, and a Debt bar for every month", () => {
    const { container } = render(
      <IncomeVsExpensesByMonth months={twelveMonths({ 0: { income: 5240, expenses: 3810, debt: 200 } })} />,
    );

    const incomeBars = container.querySelectorAll('g[fill="var(--color-accent-2-500)"] rect');
    const expenseBars = container.querySelectorAll('g[fill="var(--color-negative-fill)"] rect');
    const debtBars = container.querySelectorAll('g[fill="var(--color-debt)"] rect');
    expect(incomeBars).toHaveLength(12);
    expect(expenseBars).toHaveLength(12);
    expect(debtBars).toHaveLength(12);
  });

  it("draws a Bills & Subscriptions bar for every month, scaled like the others", () => {
    const { container } = render(
      <IncomeVsExpensesByMonth
        months={twelveMonths({ 0: { income: 1000, expenses: 600, bills_subscriptions: 200, debt: 300 } })}
      />,
    );

    const billsBars = container.querySelectorAll('g[fill="var(--color-bills-subscriptions)"] rect');
    expect(billsBars).toHaveLength(12);
    // $200 against a $1,000 axis over the 240-tall plot.
    expect(billsBars[0].getAttribute("height")).toBe("48");
    expect(billsBars[1].getAttribute("height")).toBe("0");
  });

  it("renders a month with no Income, Expenses, or Debt as a zero-height bar, not an omitted one", () => {
    const { container } = render(
      <IncomeVsExpensesByMonth months={twelveMonths({ 0: { income: 5240, expenses: 3810, debt: 200 } })} />,
    );

    const incomeBars = container.querySelectorAll('g[fill="var(--color-accent-2-500)"] rect');
    const debtBars = container.querySelectorAll('g[fill="var(--color-debt)"] rect');
    // Month index 1 (August) was never overridden, so it stays zeroed.
    expect(incomeBars[1].getAttribute("height")).toBe("0");
    expect(debtBars[1].getAttribute("height")).toBe("0");
  });

  it("plots a Net line across the months", () => {
    const { container } = render(<IncomeVsExpensesByMonth months={twelveMonths()} />);

    expect(container.querySelector("path[stroke='var(--color-chart-line)']")).toBeInTheDocument();
  });

  it("leaves Bills & Subscriptions out of the bars and the legend while no month has any", () => {
    const { container } = render(
      <IncomeVsExpensesByMonth months={twelveMonths({ 0: { income: 5240, expenses: 3810, debt: 200 } })} />,
    );

    expect(container.querySelectorAll('g[fill="var(--color-bills-subscriptions)"] rect')).toHaveLength(0);
    expect(screen.queryByText("Bills & Subscriptions")).not.toBeInTheDocument();
  });

  it("titles the card Cash Flow by Month and shows a legend for Income, Expenses, Bills & Subscriptions, Debt, and Net", () => {
    render(<IncomeVsExpensesByMonth months={twelveMonths({ 0: { bills_subscriptions: 50 } })} />);

    expect(screen.getByText("Cash Flow by Month")).toBeInTheDocument();
    expect(screen.getByText("Income")).toBeInTheDocument();
    expect(screen.getByText("Expenses")).toBeInTheDocument();
    expect(screen.getByText("Bills & Subscriptions")).toBeInTheDocument();
    expect(screen.getByText("Debt")).toBeInTheDocument();
    expect(screen.getByText("Net")).toBeInTheDocument();
  });
});
