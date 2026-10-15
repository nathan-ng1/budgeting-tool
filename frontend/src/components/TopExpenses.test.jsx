import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import TopExpenses from "./TopExpenses.jsx";

const EXPENSES = [
  { notes: "Woolworths 5678", category: "Groceries", date: "2026-08-09", amount: 400 },
  { notes: "Shell", category: "Transport", date: "2026-08-02", amount: 100 },
];

describe("TopExpenses", () => {
  it("titles the card with the count and lists each expense with its rank, Category, date and amount", () => {
    render(<TopExpenses expenses={EXPENSES} count={5} />);

    expect(screen.getByRole("heading", { name: "Top 5 expenses" })).toBeInTheDocument();
    expect(screen.getByText("Woolworths 5678")).toBeInTheDocument();
    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("9 Aug")).toBeInTheDocument();
    expect(screen.getByText("$400")).toBeInTheDocument();
    expect(screen.getByText("01")).toBeInTheDocument();
    expect(screen.getByText("02")).toBeInTheDocument();
  });

  it("limits the rows shown to the count", () => {
    render(<TopExpenses expenses={EXPENSES} count={1} />);

    expect(screen.getByRole("heading", { name: "Top 1 expenses" })).toBeInTheDocument();
    expect(screen.queryByText("Shell")).not.toBeInTheDocument();
  });

  it("shows an empty state when there is no spending", () => {
    render(<TopExpenses expenses={[]} count={5} />);

    expect(screen.getByText("No spending recorded for this period.")).toBeInTheDocument();
  });
});
