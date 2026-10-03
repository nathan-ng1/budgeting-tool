import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import MonthByMonth from "./MonthByMonth.jsx";

function row(name) {
  return screen.getByRole("row", { name: new RegExp(name) });
}

function month(overrides) {
  return { year: 2026, month: 7, income: 0, expenses: 0, bills_subscriptions: 0, debt: 0, net_balance: 0, saved: 0, ...overrides };
}

describe("MonthByMonth", () => {
  it("renders a row per month, with Income, Expenses, Bills & Subscriptions, Debt, Net, and Saved", () => {
    render(
      <MonthByMonth
        months={[
          month({
            month: 7,
            income: 5240,
            expenses: 3810,
            bills_subscriptions: 330,
            debt: 200,
            net_balance: 900,
            saved: 900,
          }),
        ]}
      />,
    );

    expect(screen.getByRole("columnheader", { name: "Bills & Subscriptions" })).toBeInTheDocument();
    const cells = within(row("July")).getAllByRole("cell");
    expect(cells[0]).toHaveTextContent("July");
    expect(cells[1]).toHaveTextContent("$5,240");
    expect(cells[2]).toHaveTextContent("$3,810");
    expect(cells[3]).toHaveTextContent("$330");
    expect(cells[4]).toHaveTextContent("$200");
    expect(cells[5]).toHaveTextContent("+$900");
    expect(cells[6]).toHaveTextContent("$900");
  });

  it("shows an unelapsed, zero-filled month as $0 rather than a signed +$0", () => {
    render(<MonthByMonth months={[month({ month: 9 })]} />);

    const cells = within(row("September")).getAllByRole("cell");
    expect(cells[5]).toHaveTextContent("$0");
    expect(cells[5]).not.toHaveTextContent("+$0");
  });

  it("computes a Total row client-side, summing every month, including Bills & Subscriptions and Debt", () => {
    render(
      <MonthByMonth
        months={[
          month({
            month: 7,
            income: 5240,
            expenses: 3810,
            bills_subscriptions: 330,
            debt: 200,
            net_balance: 900,
            saved: 900,
          }),
          month({
            month: 8,
            income: 5240,
            expenses: 3402,
            bills_subscriptions: 1100,
            debt: 150,
            net_balance: 588,
            saved: 900,
          }),
        ]}
      />,
    );

    const totals = within(row("Total")).getAllByRole("cell");
    expect(totals[1]).toHaveTextContent("$10,480");
    expect(totals[2]).toHaveTextContent("$7,212");
    expect(totals[3]).toHaveTextContent("$1,430");
    expect(totals[4]).toHaveTextContent("$350");
    expect(totals[5]).toHaveTextContent("+$1,488");
    expect(totals[6]).toHaveTextContent("$1,800");
  });

  it("colours a negative Net Balance as adverse, the opposite of an overspend Diff", () => {
    render(<MonthByMonth months={[month({ month: 12, income: 5240, expenses: 5900, net_balance: -660 })]} />);

    const cells = within(row("December")).getAllByRole("cell");
    expect(cells[5]).toHaveTextContent("−$660");
    expect(cells[5].className).toContain("figure--adverse");
  });
});
