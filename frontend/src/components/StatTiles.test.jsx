import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import StatTiles from "./StatTiles.jsx";

function tiles(overrides = {}) {
  return {
    income: 5240,
    expenses: 3667,
    bills_subscriptions: 412,
    debt: 875,
    available_to_save: 286,
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
    render(<StatTiles tiles={tiles({ income: 2000 })} average={tiles({ income: 1000, available_to_save: 700 })} />);

    expect(screen.getByText("$2,000")).toBeInTheDocument();
    expect(screen.getByText("$1,000 / month average")).toBeInTheDocument();
    expect(screen.getByText("$700 / month average")).toBeInTheDocument();
    expect(screen.queryByText(/includes savings/)).not.toBeInTheDocument();
  });

  it("labels the cashflow tile Available to Save, signed and coloured by direction", () => {
    const { rerender } = render(<StatTiles tiles={tiles({ available_to_save: 286 })} />);

    const value = () => screen.getByText("Available to Save").nextElementSibling;
    expect(screen.queryByText("Net Balance")).not.toBeInTheDocument();
    expect(value()).toHaveTextContent("+$286");
    expect(value().className).toContain("figure--favourable");

    rerender(<StatTiles tiles={tiles({ available_to_save: -120 })} />);
    expect(value()).toHaveTextContent("−$120");
    expect(value().className).toContain("figure--adverse");
  });

  it("shows an exactly balanced Available to Save as a plain $0", () => {
    render(<StatTiles tiles={tiles({ available_to_save: 0 })} />);

    const value = screen.getByText("Available to Save").nextElementSibling;
    expect(value.textContent).toBe("$0");
    expect(value.className).not.toContain("figure--");
  });

  it("orders the Bills & Subscriptions tile between Expenses and Debt", () => {
    const { container } = render(<StatTiles tiles={tiles()} />);

    const labels = [...container.querySelectorAll(".tile__label")].map((el) => el.textContent);
    expect(labels).toEqual(["Real Income", "Expenses", "Bills & Subscriptions", "Debt", "Available to Save", "Saved"]);
  });

  it("shows a Bills & Subscriptions monthly average in the Full year view", () => {
    render(<StatTiles tiles={tiles()} average={tiles({ bills_subscriptions: 137 })} />);

    expect(screen.getByText("$137 / month average")).toBeInTheDocument();
  });
});
