import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import BudgetSuggestion from "./BudgetSuggestion.jsx";

describe("BudgetSuggestion", () => {
  it("renders the stored write-up as-is, with its own line breaks preserved", () => {
    render(
      <BudgetSuggestion
        suggestion={{
          write_up: "Groceries has run over budget.\n\nTransport has tracked close to plan.",
          generated_at: "2026-08-20T14:32:00",
        }}
      />,
    );

    expect(screen.getByText(/Groceries has run over budget\./)).toHaveClass("budget-suggestion__write-up");
    expect(screen.getByText(/Groceries has run over budget\./).textContent).toBe(
      "Groceries has run over budget.\n\nTransport has tracked close to plan.",
    );
  });

  it("shows when the write-up was generated", () => {
    render(<BudgetSuggestion suggestion={{ write_up: "Some advice.", generated_at: "2026-08-20T14:32:00" }} />);

    expect(screen.getByText(/Generated 20 Aug 2026, 2:32pm/)).toBeInTheDocument();
  });

  it("shows a coherent empty state, not an error, when no write-up has ever been generated", () => {
    render(<BudgetSuggestion suggestion={null} />);

    expect(screen.getByText(/No Budget Suggestion yet/)).toBeInTheDocument();
    expect(screen.getByText("uv run python -m budget_suggestions")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
