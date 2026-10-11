import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { SettingsProvider } from "../lib/settings.jsx";
import Movers from "./Movers.jsx";

const MOVERS = {
  previous_month: [
    { category: "Dining", actual: 300, comparison: 200, diff: 100, pct: 50 },
    { category: "Groceries", actual: 450, comparison: 500, diff: -50, pct: -10 },
  ],
  avg_3_months: [
    { category: "Dining", actual: 300, comparison: 150, diff: 150, pct: 100 },
    { category: "Travel", actual: 80, comparison: 0, diff: 80, pct: null },
    { category: "Groceries", actual: 450, comparison: 450, diff: 0, pct: 0 },
  ],
  avg_12_months: [{ category: "Dining", actual: 300, comparison: 250, diff: 50, pct: 20 }],
};

const NO_MOVERS = { previous_month: [], avg_3_months: [], avg_12_months: [] };

function rowFor(category) {
  return screen.getByText(category).closest("[data-testid='mover-row']");
}

describe("Movers", () => {
  it("titles the card and offers the three comparisons, defaulting to the 3-month average", () => {
    render(<Movers movers={MOVERS} />);

    expect(screen.getByRole("heading", { name: "Movers" })).toBeInTheDocument();
    const select = screen.getByRole("combobox", { name: "Compare against" });
    expect(within(select).getAllByRole("option").map((option) => option.textContent)).toEqual([
      "Previous month",
      "Avg of preceding 3 months",
      "Avg of preceding 12 months",
    ]);
    expect(select).toHaveValue("avg_3_months");
    expect(screen.getByText("vs the average of the preceding 3 months")).toBeInTheDocument();
  });

  it("shows both Difference columns with a signed dollar and percentage figure per Category", () => {
    render(<Movers movers={MOVERS} />);

    expect(screen.getByText("Difference ($)")).toBeInTheDocument();
    expect(screen.getByText("Difference (%)")).toBeInTheDocument();
    const dining = rowFor("Dining");
    expect(within(dining).getByText("+$150")).toBeInTheDocument();
    expect(within(dining).getByText("+100%")).toBeInTheDocument();
  });

  it("switches the rows and the basis line when the comparison changes", async () => {
    render(<Movers movers={MOVERS} />);

    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Compare against" }), "previous_month");

    expect(screen.getByText("vs the previous month")).toBeInTheDocument();
    expect(screen.queryByText("Travel")).not.toBeInTheDocument();
    const groceries = rowFor("Groceries");
    expect(within(groceries).getByText("−$50")).toBeInTheDocument();
    expect(within(groceries).getByText("−10%")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Compare against" }), "avg_12_months");

    expect(screen.getByText("vs the average of the preceding 12 months")).toBeInTheDocument();
    expect(within(rowFor("Dining")).getByText("+20%")).toBeInTheDocument();
    expect(screen.queryByText("Groceries")).not.toBeInTheDocument();
  });

  it("says New for a Category with no comparison amount", () => {
    render(<Movers movers={MOVERS} />);

    const travel = rowFor("Travel");
    expect(within(travel).getByText("+$80")).toBeInTheDocument();
    expect(within(travel).getByText("New")).toBeInTheDocument();
  });

  it("shows a dash in both columns for an unchanged Category", () => {
    render(<Movers movers={MOVERS} />);

    expect(within(rowFor("Groceries")).getAllByText("—")).toHaveLength(2);
  });

  it("keeps the rows in the order the backend ranked them", () => {
    render(<Movers movers={MOVERS} />);

    expect(screen.getAllByTestId("mover-row").map((row) => row.querySelector(".movers__name").textContent)).toEqual([
      "Dining",
      "Travel",
      "Groceries",
    ]);
  });

  it("draws a bar rising on the right of the centre line and falling on the left, scaled to the largest difference", async () => {
    render(<Movers movers={MOVERS} />);
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Compare against" }), "previous_month");

    const rising = rowFor("Dining").querySelector(".movers__bar");
    const falling = rowFor("Groceries").querySelector(".movers__bar");
    expect(rising).toHaveClass("movers__bar--up");
    expect(rising).toHaveStyle({ width: "50%" });
    expect(falling).toHaveClass("movers__bar--down");
    expect(falling).toHaveStyle({ width: "25%" });
  });

  it("formats amounts in the Display Currency", () => {
    render(
      <SettingsProvider settings={{ currency: "EUR", financial_year_start_month: 7, date_order: "day-first" }}>
        <Movers movers={MOVERS} />
      </SettingsProvider>,
    );

    expect(within(rowFor("Dining")).getByText(/\+150\s€/)).toBeInTheDocument();
  });

  it("shows a friendly empty state when there is nothing to compare", () => {
    render(<Movers movers={NO_MOVERS} />);

    expect(screen.getByRole("heading", { name: "Movers" })).toBeInTheDocument();
    expect(screen.getByText("No Spending to compare for this month.")).toBeInTheDocument();
    expect(screen.queryByTestId("mover-row")).not.toBeInTheDocument();
  });
});
