import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import IncomeAllocation from "./IncomeAllocation.jsx";

function allocation(overrides = {}) {
  return {
    expenses_amount: 0,
    expenses_pct: 0,
    debt_amount: 0,
    debt_pct: 0,
    transferred_amount: 0,
    transferred_pct: 0,
    remaining_amount: 0,
    remaining_pct: 0,
    over_income_amount: 0,
    over_income_pct: 0,
    ...overrides,
  };
}

describe("IncomeAllocation", () => {
  it("splits income across what was spent, transferred and left over", () => {
    render(
      <IncomeAllocation
        income={5240}
        allocation={allocation({
          expenses_amount: 3667,
          expenses_pct: 70,
          transferred_amount: 900,
          transferred_pct: 17.2,
          remaining_amount: 673,
          remaining_pct: 12.8,
        })}
      />,
    );

    expect(screen.getByText("Expenses")).toBeInTheDocument();
    expect(screen.getByText("70.0%")).toBeInTheDocument();
    expect(screen.getByText("Remaining")).toBeInTheDocument();
  });

  it("renders a Debt segment ordered between Expenses and Transferred", () => {
    render(
      <IncomeAllocation
        income={5240}
        allocation={allocation({
          expenses_amount: 2000,
          expenses_pct: 38.2,
          debt_amount: 800,
          debt_pct: 15.3,
          transferred_amount: 900,
          transferred_pct: 17.2,
          remaining_amount: 1540,
          remaining_pct: 29.4,
        })}
      />,
    );

    // Each legend item's own direct text node is just its label - the percentage
    // lives in a nested span - so matching on direct text (not full textContent,
    // which would also pick up the nested percentage) gives the label order.
    const legendLabels = screen
      .getAllByText(/^(Expenses|Debt|Transferred|Remaining)$/)
      .map((el) => el.textContent.trim().split(" ")[0]);
    expect(legendLabels).toEqual(["Expenses", "Debt", "Transferred", "Remaining"]);
    expect(screen.getByText("15.3%")).toBeInTheDocument();
  });

  it("says how far past income the month went when outflows exceeded it", () => {
    render(
      <IncomeAllocation
        income={5240}
        allocation={allocation({
          expenses_amount: 6000,
          expenses_pct: 114.5,
          over_income_amount: 760,
          over_income_pct: 14.5,
        })}
      />,
    );

    expect(screen.getByText("Over income")).toBeInTheDocument();
    expect(screen.getByText(/\$760/)).toBeInTheDocument();
    expect(screen.queryByText("Remaining")).not.toBeInTheDocument();
  });

  it("does not report a month with no income but real spending as 0% spent", () => {
    // The endpoint zeroes every percentage when there is no Income to take a
    // share of. Rendering that as "Expenses 0.0%" beside an empty bar would
    // read as "nothing was spent" when $2,000 was.
    render(<IncomeAllocation income={0} allocation={allocation({ expenses_amount: 2000 })} />);

    expect(screen.queryByText("0.0%")).not.toBeInTheDocument();
    expect(screen.getByText(/No income recorded for this month/i)).toHaveTextContent("$2,000");
  });

  it("mentions debt repayments in the no-income message when there was Debt outflow", () => {
    render(<IncomeAllocation income={0} allocation={allocation({ debt_amount: 800 })} />);

    expect(screen.getByText(/No income recorded for this month/i)).toHaveTextContent("$800");
  });

  it("is plain about a month with neither income nor outflows", () => {
    render(<IncomeAllocation income={0} allocation={allocation()} />);

    expect(screen.getByText("No income recorded for this month.")).toBeInTheDocument();
  });
});
