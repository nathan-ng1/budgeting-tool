import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import TopMerchants from "./TopMerchants.jsx";

const MERCHANTS = [
  { merchant: "Woolworths 5678", category: "Groceries", total: 400, count: 8 },
  { merchant: "Shell", category: "Transport", total: 100, count: 2 },
];

describe("TopMerchants", () => {
  it("lists each merchant with its rank, Category and total", () => {
    render(<TopMerchants merchants={MERCHANTS} count={5} />);

    expect(screen.getByRole("heading", { name: "Top merchants" })).toBeInTheDocument();
    expect(screen.getByText("Woolworths 5678")).toBeInTheDocument();
    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("$400")).toBeInTheDocument();
    expect(screen.getByText("01")).toBeInTheDocument();
    expect(screen.getByText("02")).toBeInTheDocument();
  });

  it("sizes each bar against the top merchant", () => {
    render(<TopMerchants merchants={MERCHANTS} count={5} />);

    const bars = screen.getAllByTestId("merchant-bar");
    expect(bars[0]).toHaveStyle({ width: "100%" });
    expect(bars[1]).toHaveStyle({ width: "25%" });
  });

  it("limits the rows shown to the count", () => {
    render(<TopMerchants merchants={MERCHANTS} count={1} />);

    expect(screen.queryByText("Shell")).not.toBeInTheDocument();
  });

  it("hides the transaction count by default and shows it when toggled", () => {
    render(<TopMerchants merchants={MERCHANTS} count={5} />);

    expect(screen.queryByText("8 ×")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", { name: "Show transaction count" }));

    expect(screen.getByText("8 ×")).toBeInTheDocument();
    expect(screen.getByText("2 ×")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("checkbox", { name: "Show transaction count" }));

    expect(screen.queryByText("8 ×")).not.toBeInTheDocument();
  });

  it("shows an empty state when there is no spending", () => {
    render(<TopMerchants merchants={[]} count={5} />);

    expect(screen.getByText("No spending recorded for this period.")).toBeInTheDocument();
  });
});
