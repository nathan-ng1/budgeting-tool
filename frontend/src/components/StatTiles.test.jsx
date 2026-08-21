import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import StatTiles from "./StatTiles.jsx";

function tiles(overrides = {}) {
  return { income: 5240, expenses: 3667, net_balance: 1573, transferred: 900, ...overrides };
}

describe("StatTiles", () => {
  it("renders the four totals with no average line by default", () => {
    render(<StatTiles tiles={tiles()} />);

    expect(screen.getByText("$5,240")).toBeInTheDocument();
    expect(screen.getByText("$3,667")).toBeInTheDocument();
    expect(screen.queryByText(/month average/)).not.toBeInTheDocument();
    expect(screen.queryByText(/excludes transfers/)).not.toBeInTheDocument();
  });

  it("shows a monthly average under each tile when one is supplied", () => {
    render(<StatTiles tiles={tiles({ income: 2000 })} average={tiles({ income: 1000, net_balance: 700 })} />);

    expect(screen.getByText("$2,000")).toBeInTheDocument();
    expect(screen.getByText("$1,000 / month average")).toBeInTheDocument();
    expect(screen.getByText("$700 / month · excludes transfers")).toBeInTheDocument();
  });
});
