import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import DebtSummary from "./DebtSummary.jsx";

describe("DebtSummary", () => {
  it("shows the period's total Debt in the card head, with no average by default", () => {
    render(
      <DebtSummary
        debtSummary={[{ notes: "Werribee", amount: 1600, pct_of_debt: 100 }]}
        total={1600}
      />,
    );

    expect(screen.getByRole("heading", { name: "Debt" })).toBeInTheDocument();
    expect(screen.getAllByText("$1,600").length).toBeGreaterThan(0);
    expect(screen.queryByText(/month average/)).not.toBeInTheDocument();
  });

  it("shows a $/month average in the card head when one is supplied, for Full year", () => {
    render(
      <DebtSummary
        debtSummary={[{ notes: "Werribee", amount: 1600, pct_of_debt: 100 }]}
        total={1600}
        average={800}
      />,
    );

    expect(screen.getByText("$800 / month average")).toBeInTheDocument();
  });

  it("renders one row per payee, summed and ordered by amount descending", () => {
    render(
      <DebtSummary
        debtSummary={[
          { notes: "Werribee", amount: 1600, pct_of_debt: 76.2 },
          { notes: "Investment property", amount: 500, pct_of_debt: 23.8 },
        ]}
        total={2100}
      />,
    );

    const names = screen.getAllByTitle(/Werribee|Investment property/).map((el) => el.textContent);
    expect(names).toEqual(["Werribee", "Investment property"]);
    expect(screen.getByText("$1,600")).toBeInTheDocument();
    expect(screen.getByText("$500")).toBeInTheDocument();
  });

  it("renders an empty state instead of a broken card when there are no Debt Transactions", () => {
    render(<DebtSummary debtSummary={[]} total={0} />);

    expect(screen.getByText(/No Debt repayments recorded/i)).toBeInTheDocument();
  });
});
