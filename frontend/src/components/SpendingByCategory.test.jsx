import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import SpendingByCategory from "./SpendingByCategory.jsx";

describe("SpendingByCategory", () => {
  it("shows a Category's emoji next to its name in the legend when one is set", () => {
    render(
      <SpendingByCategory
        spending={[{ category: "Groceries", amount: 612, pct_of_expenses: 100 }]}
        total={612}
        categories={[{ id: 1, type: "Expense", name: "Groceries", emoji: "🛒", locked: false }]}
      />,
    );

    expect(screen.getByText("🛒 Groceries")).toBeInTheDocument();
  });

  it("shows just the name when a Category has no emoji", () => {
    render(
      <SpendingByCategory
        spending={[{ category: "Groceries", amount: 612, pct_of_expenses: 100 }]}
        total={612}
        categories={[{ id: 1, type: "Expense", name: "Groceries", emoji: null, locked: false }]}
      />,
    );

    expect(screen.getByText("Groceries")).toBeInTheDocument();
  });
});
