import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SettingsProvider } from "../lib/settings.jsx";
import RecurringCharges from "./RecurringCharges.jsx";

const RECURRING = {
  per_year: 1457.68,
  per_month: 121.47,
  rows: [
    { merchant: "Anytime Fitness", category: "Gym", charges: 11, last_charged: "2026-09-21", typical: 37.5, cadence_days: 14, per_year: 977.68 },
    { merchant: "Car Insurance", category: "Insurance", charges: 1, last_charged: "2026-03-10", typical: 480, cadence_days: null, per_year: 480 },
  ],
};

describe("RecurringCharges", () => {
  it("titles the card and shows the total per year and per month in the header", () => {
    render(<RecurringCharges recurring={RECURRING} />);

    expect(screen.getByRole("heading", { name: "Recurring Charges" })).toBeInTheDocument();
    expect(screen.getByText("$1,458 / year")).toBeInTheDocument();
    expect(screen.getByText("$121 / month")).toBeInTheDocument();
  });

  it("lists each merchant with its Category, charge count, last charged date, typical charge and yearly cost", () => {
    render(<RecurringCharges recurring={RECURRING} />);

    const gym = screen.getByText("Anytime Fitness").closest("tr");
    expect(within(gym).getByText("Gym")).toBeInTheDocument();
    expect(within(gym).getByText("11")).toBeInTheDocument();
    expect(within(gym).getByText("21 Sep")).toBeInTheDocument();
    expect(within(gym).getByText("$37.50")).toBeInTheDocument();
    expect(within(gym).getByText("$978")).toBeInTheDocument();
  });

  it("says how often a charge recurs, or that it had one charge", () => {
    render(<RecurringCharges recurring={RECURRING} />);

    expect(within(screen.getByText("Anytime Fitness").closest("tr")).getByText("Every 14 days")).toBeInTheDocument();
    expect(within(screen.getByText("Car Insurance").closest("tr")).getByText("1 charge")).toBeInTheDocument();
  });

  it("shows the charge count, not 1 charge, when several charges share one date", () => {
    const sameDay = {
      per_year: 90,
      per_month: 7.5,
      rows: [{ merchant: "Double Billed", category: "Insurance", charges: 3, last_charged: "2026-03-10", typical: 30, cadence_days: null, per_year: 90 }],
    };
    render(<RecurringCharges recurring={sameDay} />);

    expect(within(screen.getByText("Double Billed").closest("tr")).getByText("3 charges")).toBeInTheDocument();
  });

  it("keeps the rows in the order the backend ranked them", () => {
    render(<RecurringCharges recurring={RECURRING} />);

    const names = screen.getAllByTestId("recurring-merchant").map((cell) => cell.textContent);
    expect(names).toEqual(["Anytime Fitness", "Car Insurance"]);
  });

  it("colours each Category dot from the shared mapping", () => {
    const colourFor = (category) => (category === "Gym" ? "rgb(1, 2, 3)" : "rgb(4, 5, 6)");
    render(<RecurringCharges recurring={RECURRING} colourFor={colourFor} />);

    const dot = screen.getByText("Anytime Fitness").closest("tr").querySelector(".dot");
    expect(dot).toHaveStyle({ background: "rgb(1, 2, 3)" });
  });

  it("formats amounts in the Display Currency and dates in the chosen Date Order", () => {
    render(
      <SettingsProvider settings={{ currency: "EUR", financial_year_start_month: 7, date_order: "month-first" }}>
        <RecurringCharges recurring={RECURRING} />
      </SettingsProvider>,
    );

    expect(screen.getByText("Sep 21")).toBeInTheDocument();
    expect(screen.getByText(/1.458\s€ \/ year/)).toBeInTheDocument();
  });

  it("shows a friendly empty state when there are no Bills & Subscriptions", () => {
    render(<RecurringCharges recurring={{ per_year: 0, per_month: 0, rows: [] }} />);

    expect(screen.getByRole("heading", { name: "Recurring Charges" })).toBeInTheDocument();
    expect(screen.getByText("No Bills & Subscriptions recorded in the last 12 months.")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});
