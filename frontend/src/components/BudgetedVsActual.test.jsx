import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import BudgetedVsActual from "./BudgetedVsActual.jsx";

function row(name) {
  return screen.getByRole("row", { name: new RegExp(name) });
}

function sectionHeading(name) {
  return screen.getByRole("columnheader", { name });
}

describe("BudgetedVsActual", () => {
  it("shows a Category with no Category Budget set as unset, not as a $0 target", () => {
    render(
      <BudgetedVsActual
        rows={[{ type: "Expense", category: "Groceries", budgeted: null, actual: 612, diff: null, pct: null }]}
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

  it("reads Diff and % as actual against budgeted, the way the mockup shows them", () => {
    // The endpoint computes diff as `budgeted - actual` (budget remaining) and
    // pct as `actual / budgeted * 100`; the table reads the other way round -
    // a positive Diff means actual came in above budgeted.
    render(
      <BudgetedVsActual
        rows={[
          { type: "Expense", category: "Groceries", budgeted: 650, actual: 612, diff: 38, pct: 94.2 },
          { type: "Expense", category: "Transport", budgeted: 220, actual: 260, diff: -40, pct: 118.2 },
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

  it("shows 0% Diff, not -100%, when both Budgeted and Actual are $0", () => {
    // The endpoint's pct is undefined when budgeted is $0 and falls back to
    // 0, which the table's usual `pct - 100` reading would show as -100% -
    // wrong when there's genuinely nothing to compare (both sides are $0).
    render(
      <BudgetedVsActual
        rows={[{ type: "Expense", category: "Rental Expense", budgeted: 0, actual: 0, diff: 0, pct: 0 }]}
      />,
    );

    const cells = within(row("Rental Expense")).getAllByRole("cell");
    expect(cells[4]).toHaveTextContent("+$0");
    expect(cells[5]).toHaveTextContent("+0%");
    expect(cells[5]).not.toHaveTextContent("-100%");
  });

  it("partitions rows into Income, Expense, and Debt sections, each with its own subtotal", () => {
    render(
      <BudgetedVsActual
        rows={[
          { type: "Expense", category: "Groceries", budgeted: 650, actual: 612, diff: 38, pct: 94.2 },
          { type: "Income", category: "Salary", budgeted: 4000, actual: 4200, diff: -200, pct: 105.0 },
          { type: "Debt", category: "Mortgage Repayment", budgeted: 850, actual: 900, diff: -50, pct: 105.9 },
        ]}
      />,
    );

    expect(sectionHeading("Income")).toBeInTheDocument();
    expect(sectionHeading("Expense")).toBeInTheDocument();
    expect(sectionHeading("Debt")).toBeInTheDocument();

    expect(within(row("Income total")).getAllByRole("cell")[2]).toHaveTextContent("$4,000");
    expect(within(row("Expense total")).getAllByRole("cell")[2]).toHaveTextContent("$650");
    expect(within(row("Debt total")).getAllByRole("cell")[2]).toHaveTextContent("$850");

    // No grand total across Types.
    expect(screen.queryByText(/^Total$/)).not.toBeInTheDocument();
  });

  it("omits a section entirely when it has no rows", () => {
    render(
      <BudgetedVsActual
        rows={[{ type: "Expense", category: "Groceries", budgeted: 650, actual: 612, diff: 38, pct: 94.2 }]}
      />,
    );

    expect(screen.queryByRole("columnheader", { name: "Income" })).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Debt" })).not.toBeInTheDocument();
  });

  it("reads an Income Category over its Budgeted as favourable, unlike Expense/Debt", () => {
    render(
      <BudgetedVsActual
        rows={[
          { type: "Income", category: "Salary", budgeted: 4000, actual: 4200, diff: -200, pct: 105.0 },
          { type: "Expense", category: "Groceries", budgeted: 650, actual: 700, diff: -50, pct: 107.7 },
        ]}
      />,
    );

    const incomeDiffCell = within(row("Salary")).getAllByRole("cell")[4];
    const expenseDiffCell = within(row("Groceries")).getAllByRole("cell")[4];

    // Both actuals landed above Budgeted (a positive Diff), but that reads as
    // favourable for Income and adverse for Expense.
    expect(incomeDiffCell).toHaveTextContent("+$200");
    expect(incomeDiffCell.className).toContain("favourable");
    expect(expenseDiffCell).toHaveTextContent("+$50");
    expect(expenseDiffCell.className).toContain("adverse");
  });

  it("totals Budgeted and Diff from budgeted Categories only, but Actual from every Category in the section", () => {
    render(
      <BudgetedVsActual
        rows={[
          { type: "Expense", category: "Groceries", budgeted: 650, actual: 612, diff: 38, pct: 94.2 },
          { type: "Expense", category: "Transport", budgeted: null, actual: 100, diff: null, pct: null },
        ]}
      />,
    );

    const totals = within(row("Expense total")).getAllByRole("cell");

    // Unbudgeted Transport is excluded from Budgeted/Diff: charging its spend
    // against a budgeted-only total would read as an overspend that isn't
    // one. Actual isn't a comparison though - it's the section's real total
    // spend, so it includes Transport.
    expect(totals[2]).toHaveTextContent("$650");
    expect(totals[3]).toHaveTextContent("$712");
    expect(totals[4]).toHaveTextContent("−$38");
  });

  it("still totals real Actual spend even when no Category in the section has a Category Budget", () => {
    render(
      <BudgetedVsActual
        rows={[
          { type: "Income", category: "Salary", budgeted: null, actual: 16943, diff: null, pct: null },
          { type: "Income", category: "Beem Adjustment", budgeted: null, actual: 492, diff: null, pct: null },
        ]}
      />,
    );

    const totals = within(row("Income total")).getAllByRole("cell");

    expect(totals[2]).toHaveTextContent("—");
    expect(totals[3]).toHaveTextContent("$17,435");
    expect(totals[4]).toHaveTextContent("—");
  });

  it("orders rows within a section by spend, so the table lines up with the donut legend beside it", () => {
    render(
      <BudgetedVsActual
        rows={[
          { type: "Expense", category: "Groceries", budgeted: 650, actual: 100, diff: 550, pct: 15.4 },
          { type: "Expense", category: "Transport", budgeted: 220, actual: 900, diff: -680, pct: 409.1 },
        ]}
      />,
    );

    // Row 0 is the table header, row 1 is the "Expense" section heading -
    // the two Category rows follow.
    const names = screen.getAllByRole("row").slice(2, 4).map((r) => within(r).getAllByRole("cell")[1].textContent);

    expect(names).toEqual(["Transport", "Groceries"]);
  });

  it("shows a Category's emoji next to its name when one is set", () => {
    render(
      <BudgetedVsActual
        rows={[{ type: "Expense", category: "Groceries", budgeted: 650, actual: 612, diff: 38, pct: 94.2 }]}
        categories={[{ id: 1, type: "Expense", name: "Groceries", emoji: "🛒", locked: false }]}
      />,
    );

    expect(within(row("Groceries")).getAllByRole("cell")[1]).toHaveTextContent("🛒 Groceries");
  });

  it("says so plainly when there is nothing to compare yet", () => {
    render(<BudgetedVsActual rows={[]} />);

    expect(screen.getByText(/no spending or Category Budgets/i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  describe("total Diff", () => {
    function figure() {
      return screen.getByText("Total Diff").closest(".card__aside").querySelector(".card__aside-figure");
    }

    it("sums Diff across every Type, budgeted Categories only", () => {
      render(
        <BudgetedVsActual
          rows={[
            { type: "Income", category: "Salary", budgeted: 4000, actual: 4000, diff: 0, pct: 100 },
            { type: "Expense", category: "Groceries", budgeted: 650, actual: 600, diff: 50, pct: 92.3 },
            { type: "Expense", category: "Transport", budgeted: null, actual: 900, diff: null, pct: null },
            { type: "Debt", category: "Mortgage Repayment", budgeted: 850, actual: 850, diff: 0, pct: 100 },
          ]}
        />,
      );

      // Only budgeted Categories count: (4000-4000) + (600-650) + (850-850) = -50.
      expect(figure()).toHaveTextContent("−$50");
    });

    it("colours a negative total (actual under budgeted) favourable", () => {
      render(
        <BudgetedVsActual
          rows={[{ type: "Expense", category: "Groceries", budgeted: 650, actual: 600, diff: 50, pct: 92.3 }]}
        />,
      );

      expect(figure().className).toContain("favourable");
      expect(figure()).not.toHaveTextContent("+");
    });

    it("colours a positive total (actual over budgeted) adverse", () => {
      render(
        <BudgetedVsActual
          rows={[{ type: "Expense", category: "Groceries", budgeted: 650, actual: 700, diff: -50, pct: 107.7 }]}
        />,
      );

      expect(figure().className).toContain("adverse");
      expect(figure()).toHaveTextContent("+$50");
    });

    it("leaves an exactly-zero total unstyled", () => {
      render(
        <BudgetedVsActual
          rows={[{ type: "Expense", category: "Groceries", budgeted: 650, actual: 650, diff: 0, pct: 100 }]}
        />,
      );

      expect(figure().className).not.toContain("favourable");
      expect(figure().className).not.toContain("adverse");
    });

    it("shows unset, not $0, when no Category anywhere has a Category Budget", () => {
      render(
        <BudgetedVsActual
          rows={[{ type: "Expense", category: "Groceries", budgeted: null, actual: 700, diff: null, pct: null }]}
        />,
      );

      expect(figure()).toHaveTextContent("—");
      expect(figure()).not.toHaveTextContent("$0");
    });

    it("omits the total figure entirely when there is nothing to compare yet", () => {
      render(<BudgetedVsActual rows={[]} />);

      expect(screen.queryByText("Total Diff")).not.toBeInTheDocument();
    });
  });
});
