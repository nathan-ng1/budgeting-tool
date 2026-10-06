import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import BalanceCheck from "./BalanceCheck.jsx";

function tiles(overrides = {}) {
  return {
    income: 5000,
    expenses: 2500,
    bills_subscriptions: 500,
    debt: 1000,
    available_to_save: 1000,
    saved: 800,
    unallocated: 200,
    ...overrides,
  };
}

describe("BalanceCheck", () => {
  it("shows a positive Unallocated amount signed and neutral, with no chip", () => {
    render(<BalanceCheck tiles={tiles({ unallocated: 200 })} />);

    expect(screen.getByText("Unallocated")).toBeInTheDocument();
    const figure = screen.getByText("+$200");
    expect(figure).not.toHaveClass("figure--adverse");
    expect(screen.queryByText("Balanced")).not.toBeInTheDocument();
    expect(screen.queryByText("Over income")).not.toBeInTheDocument();
  });

  it("shows exactly $0 unsigned with a Balanced chip", () => {
    render(<BalanceCheck tiles={tiles({ saved: 1000, unallocated: 0 })} />);

    expect(screen.getByText("$0")).toBeInTheDocument();
    expect(screen.getByText("Balanced")).toBeInTheDocument();
    expect(screen.queryByText("Over income")).not.toBeInTheDocument();
  });

  it("shows a negative Unallocated amount signed and adverse, with an Over income chip", () => {
    render(<BalanceCheck tiles={tiles({ saved: 1250, unallocated: -250 })} />);

    expect(screen.getByText("−$250")).toHaveClass("figure--adverse");
    expect(screen.getByText("Over income")).toBeInTheDocument();
    expect(screen.queryByText("Balanced")).not.toBeInTheDocument();
  });

  it("captions how much was saved out of what was available to save, with the share", () => {
    render(<BalanceCheck tiles={tiles({ available_to_save: 1000, saved: 800 })} />);

    expect(screen.getByText("Saved $800 of $1,000 available to save (80%)")).toBeInTheDocument();
  });

  it("omits the share when nothing was available to save", () => {
    render(<BalanceCheck tiles={tiles({ available_to_save: -300, saved: 0, unallocated: -300 })} />);

    expect(screen.getByText("Saved $0 of $0 available to save")).toBeInTheDocument();
  });

  it("shows no monthly average line for a single month", () => {
    render(<BalanceCheck tiles={tiles()} />);

    expect(screen.queryByText(/month average/)).not.toBeInTheDocument();
  });

  it("shows the year-to-date total with a per-month average on Full year", () => {
    render(
      <BalanceCheck
        tiles={tiles({ available_to_save: 2000, saved: 2600, unallocated: -600 })}
        average={tiles({ available_to_save: 1000, saved: 1300, unallocated: -300 })}
      />,
    );

    expect(screen.getByText("−$600")).toBeInTheDocument();
    expect(screen.getByText("−$300 / month average")).toBeInTheDocument();
  });
});
