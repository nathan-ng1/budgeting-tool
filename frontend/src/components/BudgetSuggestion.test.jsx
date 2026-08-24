import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import BudgetSuggestion from "./BudgetSuggestion.jsx";

const EDITOR = {
  Expense: [
    { category: "Groceries", last_month_actual: 500, trailing_average_actual: 450, average_variance_pct: 25 },
    { category: "Transport", last_month_actual: 100, trailing_average_actual: 110, average_variance_pct: -5 },
  ],
  Income: [{ category: "Salary", last_month_actual: 4000, trailing_average_actual: 4000, average_variance_pct: 0 }],
};

describe("BudgetSuggestion", () => {
  it("renders the write-up as a bulleted list, stripping the Advisor's own bullet markers", () => {
    render(
      <BudgetSuggestion
        suggestion={{
          write_up: "- Groceries has run over budget.\n- Transport has tracked close to plan.",
          generated_at: "2026-08-20T14:32:00",
        }}
        editor={null}
      />,
    );

    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Groceries has run over budget.");
    expect(items[1]).toHaveTextContent("Transport has tracked close to plan.");
  });

  it("shows when the write-up was generated", () => {
    render(<BudgetSuggestion suggestion={{ write_up: "- Some advice.", generated_at: "2026-08-20T14:32:00" }} editor={null} />);

    expect(screen.getByText(/Generated 20 Aug 2026, 2:32pm/)).toBeInTheDocument();
  });

  it("shows Expense/Debt Category variance chips from the editor, excluding Income", () => {
    render(
      <BudgetSuggestion
        suggestion={{ write_up: "- Some advice.", generated_at: "2026-08-20T14:32:00" }}
        editor={EDITOR}
      />,
    );

    expect(screen.getByText("Groceries +25%")).toBeInTheDocument();
    expect(screen.getByText("Transport −5%")).toBeInTheDocument();
    expect(screen.queryByText(/Salary/)).not.toBeInTheDocument();
  });

  it("shows a coherent empty state for chips when there is no editor data yet", () => {
    render(
      <BudgetSuggestion
        suggestion={{ write_up: "- Some advice.", generated_at: "2026-08-20T14:32:00" }}
        editor={null}
      />,
    );

    expect(screen.getByText(/Select a month below to see Category variance chips here/)).toBeInTheDocument();
  });

  it("shows a coherent empty state, not an error, when no write-up has ever been generated", () => {
    render(<BudgetSuggestion suggestion={null} editor={null} />);

    expect(screen.getByText(/No Budget Suggestion yet/)).toBeInTheDocument();
    expect(screen.getByText("uv run python -m budget_suggestions")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
