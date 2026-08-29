import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import StatTiles from "./StatTiles.jsx";

function tiles(overrides = {}) {
  return { income: 5240, expenses: 3667, debt: 875, net_balance: 698, saved: 900, ...overrides };
}

describe("StatTiles", () => {
  it("renders the five totals with no average line by default", () => {
    render(<StatTiles tiles={tiles()} />);

    expect(screen.getByText("$5,240")).toBeInTheDocument();
    expect(screen.getByText("$3,667")).toBeInTheDocument();
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
});
