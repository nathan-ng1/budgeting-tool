import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import StatTiles from "./StatTiles.jsx";

function tiles(overrides = {}) {
  return {
    income: 5240,
    expenses: 3667,
    bills_subscriptions: 412,
    debt: 875,
    net_balance: 286,
    saved: 900,
    ...overrides,
  };
}

describe("StatTiles", () => {
  it("renders the six totals with no average line by default", () => {
    render(<StatTiles tiles={tiles()} />);

    expect(screen.getByText("$5,240")).toBeInTheDocument();
    expect(screen.getByText("$3,667")).toBeInTheDocument();
    expect(screen.getByText("Bills & Subscriptions")).toBeInTheDocument();
    expect(screen.getByText("$412")).toBeInTheDocument();
    expect(screen.getByText("Debt")).toBeInTheDocument();
    expect(screen.getByText("$875")).toBeInTheDocument();
    expect(screen.getByText("Saved")).toBeInTheDocument();
    expect(screen.queryByText(/month average/)).not.toBeInTheDocument();
    expect(screen.queryByText(/includes savings/)).not.toBeInTheDocument();
  });

  it("shows a monthly average under each tile when one is supplied", () => {
    render(<StatTiles tiles={tiles({ income: 2000 })} average={tiles({ income: 1000, net_balance: 700 })} />);

    expect(screen.getByText("$2,000")).toBeInTheDocument();
    expect(screen.getByText("$1,000 / month average")).toBeInTheDocument();
    expect(screen.getByText("$700 / month · includes savings")).toBeInTheDocument();
  });

  it("orders the Bills & Subscriptions tile between Expenses and Debt", () => {
    const { container } = render(<StatTiles tiles={tiles()} />);

    const labels = [...container.querySelectorAll(".tile__label")].map((el) => el.textContent);
    expect(labels).toEqual(["Real Income", "Expenses", "Bills & Subscriptions", "Debt", "Net Balance", "Saved"]);
  });

  it("shows a Bills & Subscriptions monthly average in the Full year view", () => {
    render(<StatTiles tiles={tiles()} average={tiles({ bills_subscriptions: 137 })} />);

    expect(screen.getByText("$137 / month average")).toBeInTheDocument();
  });
});
