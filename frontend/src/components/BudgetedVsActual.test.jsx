import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import BudgetedVsActual from "./BudgetedVsActual.jsx";

function row(name) {
  return screen.getByRole("row", { name: new RegExp(name) });
}

describe("BudgetedVsActual", () => {
  it("shows a Category with no Category Budget set as unset, not as a $0 target", () => {
    render(
      <BudgetedVsActual
        rows={[{ category: "Groceries", expected: null, actual: 612, diff: null, pct: null }]}
      />,
    );

    const cells = within(row("Groceries")).getAllByRole("cell");

    expect(cells[1]).toHaveTextContent("Groceries");
    expect(cells[2]).toHaveTextContent("—");
    expect(cells[2]).not.toHaveTextContent("$0");
    expect(cells[3]).toHaveTextContent("$612");
    // Nothing to compare against, so no Diff and no percentage either.
    expect(cells[4]).toHaveTextContent("—");
    expect(cells[5]).toHaveTextContent("—");
  });

  it("reads Diff and % as actual against expected, the way the mockup shows them", () => {
    // The endpoint computes diff as `expected - actual` (budget remaining) and
    // pct as `actual / expected * 100`; the table reads the other way round -
    // a positive Diff means overspent.
    render(
      <BudgetedVsActual
        rows={[
          { category: "Groceries", expected: 650, actual: 612, diff: 38, pct: 94.2 },
          { category: "Transport", expected: 220, actual: 260, diff: -40, pct: 118.2 },
        ]}
      />,
    );

    const under = within(row("Groceries")).getAllByRole("cell");
    expect(under[4]).toHaveTextContent("−$38");
    expect(under[5]).toHaveTextContent("−6%");

    const over = within(row("Transport")).getAllByRole("cell");
    expect(over[4]).toHaveTextContent("+$40");
    expect(over[5]).toHaveTextContent("+18%");
  });

  it("totals only the Categories that actually have a Category Budget, on both sides", () => {
    render(
      <BudgetedVsActual
        rows={[
          { category: "Groceries", expected: 650, actual: 612, diff: 38, pct: 94.2 },
          { category: "Transport", expected: null, actual: 100, diff: null, pct: null },
        ]}
      />,
    );

    const totals = within(row("Total")).getAllByRole("cell");

    // Unbudgeted Transport is excluded from BOTH columns: charging its spend
    // against a budgeted-only Expected would read as an overspend that isn't
    // one.
    expect(totals[2]).toHaveTextContent("$650");
    expect(totals[3]).toHaveTextContent("$612");
    expect(totals[4]).toHaveTextContent("−$38");
  });

  it("orders rows by spend, so the table lines up with the donut legend beside it", () => {
    render(
      <BudgetedVsActual
        rows={[
          { category: "Groceries", expected: 650, actual: 100, diff: 550, pct: 15.4 },
          { category: "Transport", expected: 220, actual: 900, diff: -680, pct: 409.1 },
        ]}
      />,
    );

    const names = screen.getAllByRole("row").slice(1, 3).map((r) => within(r).getAllByRole("cell")[1].textContent);

    expect(names).toEqual(["Transport", "Groceries"]);
  });

  it("has no Difference headline when nothing is budgeted at all", () => {
    render(<BudgetedVsActual rows={[{ category: "Groceries", expected: null, actual: 612, diff: null, pct: null }]} />);

    expect(screen.queryByText("Difference")).not.toBeInTheDocument();
  });

  it("says so plainly when there is nothing to compare yet", () => {
    render(<BudgetedVsActual rows={[]} />);

    expect(screen.getByText(/no spending or Category Budgets/i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});
