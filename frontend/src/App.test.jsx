import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App.jsx";

const ZERO_STAT_TILES = { income: 0, expenses: 0, bills_subscriptions: 0, debt: 0, available_to_save: 0, saved: 0, unallocated: 0 };
const ZERO_MONTH_TOTALS = { income: 0, expenses: 0, bills_subscriptions: 0, debt: 0, available_to_save: 0, saved: 0 };
const NO_RECURRING = { per_year: 0, per_month: 0, rows: [] };
const NO_MOVERS = { previous_month: [], avg_3_months: [], avg_12_months: [] };
const DINING_MOVERS = {
  previous_month: [{ category: "Dining", actual: 300, comparison: 200, diff: 100, pct: 50 }],
  avg_3_months: [{ category: "Dining", actual: 300, comparison: 150, diff: 150, pct: 100 }],
  avg_12_months: [{ category: "Dining", actual: 300, comparison: 250, diff: 50, pct: 20 }],
};
const GYM_RECURRING = {
  per_year: 975,
  per_month: 81.25,
  rows: [
    { merchant: "Anytime Fitness", category: "Gym", charges: 11, last_charged: "2026-08-17", typical: 37.5, cadence_days: 14, cadence: "Fortnightly", per_year: 975 },
  ],
};
const ZERO_ALLOCATION = {
  expenses_amount: 0,
  expenses_pct: 0,
  debt_amount: 0,
  debt_pct: 0,
  saved_amount: 0,
  saved_pct: 0,
  unallocated_amount: 0,
  unallocated_pct: 0,
  over_income_amount: 0,
  over_income_pct: 0,
};

function monthOverview({ year = 2026, month = 8, ...overrides } = {}) {
  return {
    year,
    month,
    stat_tiles: ZERO_STAT_TILES,
    income_allocation: ZERO_ALLOCATION,
    spending_by_category: [],
    budgeted_vs_actual: [],
    debt_summary: [],
    top_merchants: [],
    spending_over_time: { daily: [], total: 0, daily_average: 0 },
    recurring_charges: NO_RECURRING,
    movers: NO_MOVERS,
    ...overrides,
  };
}

function monthWithSpending(year, month, overrides = {}) {
  return monthOverview({
    year,
    month,
    stat_tiles: { income: 5240, expenses: 3667, bills_subscriptions: 0, debt: 0, available_to_save: 1573, saved: 900, unallocated: 673 },
    income_allocation: {
      expenses_amount: 3667,
      expenses_pct: 70,
      debt_amount: 0,
      debt_pct: 0,
      saved_amount: 900,
      saved_pct: 17.2,
      unallocated_amount: 673,
      unallocated_pct: 12.8,
      over_income_amount: 0,
      over_income_pct: 0,
    },
    spending_by_category: [{ category: "Groceries", amount: 3667, pct_of_spending: 100 }],
    budgeted_vs_actual: [{ type: "Expense", category: "Groceries", budgeted: 650, actual: 3667, diff: -3017, pct: 564.2 }],
    top_merchants: [{ merchant: "Woolworths", category: "Groceries", total: 3667, count: 4 }],
    spending_over_time: {
      daily: [
        { date: `${year}-0${month}-01`, cumulative: 0 },
        { date: `${year}-0${month}-05`, cumulative: 3667 },
      ],
      total: 3667,
      daily_average: 118,
    },
    ...overrides,
  });
}

const ZERO_MONTHS = Array.from({ length: 12 }, (_, index) => {
  const month = ((7 - 1 + index) % 12) + 1;
  return { year: month >= 7 ? 2026 : 2027, month, ...ZERO_MONTH_TOTALS };
});

function annualOverview(overrides = {}) {
  return {
    year: 2026,
    elapsed_months: 2,
    stat_tiles: ZERO_STAT_TILES,
    monthly_average: ZERO_STAT_TILES,
    income_allocation: ZERO_ALLOCATION,
    spending_by_category: [],
    budgeted_vs_actual: [],
    debt_summary: [],
    top_merchants: [],
    recurring_charges: NO_RECURRING,
    month_by_month: ZERO_MONTHS,
    income_vs_expenses_by_month: ZERO_MONTHS,
    outflows_by_month: ZERO_MONTHS,
    ...overrides,
  };
}

function annualWithSpending(overrides = {}) {
  const months = ZERO_MONTHS.map((m, index) =>
    index === 0 ? { ...m, income: 5240, expenses: 3810, debt: 0, available_to_save: 1430, saved: 900 } : m,
  );

  return annualOverview({
    stat_tiles: { income: 8000, expenses: 6000, bills_subscriptions: 0, debt: 0, available_to_save: 2000, saved: 1000, unallocated: 1000 },
    monthly_average: { income: 4000, expenses: 3000, bills_subscriptions: 0, debt: 0, available_to_save: 1000, saved: 500, unallocated: 500 },
    income_allocation: {
      expenses_amount: 6000,
      expenses_pct: 75,
      debt_amount: 0,
      debt_pct: 0,
      saved_amount: 1000,
      saved_pct: 12.5,
      unallocated_amount: 1000,
      unallocated_pct: 12.5,
      over_income_amount: 0,
      over_income_pct: 0,
    },
    spending_by_category: [{ category: "Groceries", amount: 6000, pct_of_spending: 100 }],
    // Full year's Budgeted is a real per-Category rollup across elapsed months (ADR-0013).
    budgeted_vs_actual: [{ type: "Expense", category: "Groceries", budgeted: 3000, actual: 6000, diff: -3000, pct: 200.0 }],
    top_merchants: [{ merchant: "Woolworths", category: "Groceries", total: 6000, count: 9 }],
    month_by_month: months,
    income_vs_expenses_by_month: months,
    ...overrides,
  });
}

let fetchMock;

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date(2026, 7, 21)); // 21 August 2026 - Financial Year 2026
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  localStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  localStorage.clear();
});

function routeTo(bodies) {
  fetchMock.mockImplementation(async (url) => {
    const match = Object.keys(bodies).find((path) => url.startsWith(path));
    return { ok: true, status: 200, json: async () => bodies[match] };
  });
}

// Routes every endpoint an Overview-tab load touches, with sensible defaults -
// most tests only care about overriding one of them. `extra` layers in
// endpoints beyond Overview's own, for tests that also need another tab
// wired (e.g. Budget's - see respondWithBudget below).
function respondWith({
  annual = annualWithSpending(),
  month = monthWithSpending(2026, 8),
  latestTransactionDate = "2026-08-03",
  transactionDateRange = { earliest: "2025-12-17", latest: "2026-08-03" },
  extra = {},
} = {}) {
  routeTo({
    "/api/annual-overview": annual,
    "/api/overview": month,
    "/api/latest-transaction-date": { date: latestTransactionDate },
    "/api/transaction-date-range": transactionDateRange,
    ...extra,
  });
}

describe("App", () => {
  it("opens on Full year by default, for the Financial Year containing today", async () => {
    respondWith();
    render(<App />);

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/annual-overview?year=2026&period=financial", expect.anything()),
    );

    expect(screen.getByText("2026-2027 Financial Year")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Full year" })).toHaveAttribute("aria-pressed", "true");
  });

  it("renders Full year's stat tiles and income allocation, with elapsed-month averages", async () => {
    respondWith();
    render(<App />);

    expect(await screen.findByText("$8,000")).toBeInTheDocument(); // Real Income tile
    expect(screen.getByText("$4,000 / month average")).toBeInTheDocument();
    expect(screen.getByText("$1,000 / month average")).toBeInTheDocument(); // Available to Save average
    expect(screen.queryByText(/includes savings/)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Where did my income go?" })).toBeInTheDocument();
  });

  it("renders the Balance check card's Unallocated beside the income allocation, with no Left to Budget", async () => {
    // #168 - the Overview shows actuals only; Left to Budget stays on the Budget tab.
    respondWith();
    render(<App />);
    await screen.findByText("$8,000");

    const card = screen.getByRole("region", { name: "Balance check" });
    expect(within(card).getByText("+$1,000")).toBeInTheDocument();
    expect(within(card).getByText("+$500 / month average")).toBeInTheDocument();
    expect(screen.queryByText(/Left to Budget/)).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Aug" }));
    await screen.findByText("$5,240");

    expect(within(screen.getByRole("region", { name: "Balance check" })).getByText("+$673")).toBeInTheDocument();
    expect(screen.queryByText(/month average/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Left to Budget/)).not.toBeInTheDocument();
  });

  it("renders Full year's Spending by Category, Budgeted vs Actual, Month by month, Cash Flow by Month, and Top merchants", async () => {
    respondWith();
    render(<App />);
    await screen.findByText("$8,000");

    expect(screen.getByRole("heading", { name: "Spending by Category" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Budgeted vs Actual" })).toBeInTheDocument();
    // Full year's Budgeted vs Actual now reports a real per-Category rollup,
    // not ADR-0011's placeholder "—" (ADR-0013).
    expect(screen.getByRole("row", { name: /Groceries/ })).toHaveTextContent("$3,000");

    expect(screen.getByRole("heading", { name: "Month by month" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Cash Flow by Month" })).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Top merchants" })).toBeInTheDocument();
    expect(screen.getByText("Woolworths")).toBeInTheDocument();

    // Per-month-only sections stay off Full year.
    expect(screen.queryByRole("heading", { name: "Spending over time" })).not.toBeInTheDocument();
  });

  it("selecting a month pill still shows the existing per-month Overview, unchanged", async () => {
    respondWith();
    render(<App />);
    await screen.findByText("$8,000");

    await userEvent.click(screen.getByRole("button", { name: "Aug" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/overview?year=2026&month=8", expect.anything()),
    );
    expect(await screen.findByText("$5,240")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Where did my income go?" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Spending by Category" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Budgeted vs Actual" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Top merchants" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Spending over time" })).toBeInTheDocument();
    expect(screen.getByText("Woolworths")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aug" })).toHaveAttribute("aria-pressed", "true");
  });

  it("totals the Spending by Category card as Expenses plus Bills & Subscriptions, for a month", async () => {
    respondWith({
      month: monthWithSpending(2026, 8, {
        stat_tiles: { ...ZERO_STAT_TILES, income: 5240, expenses: 3667, bills_subscriptions: 620 },
        spending_by_category: [
          { category: "Groceries", type: "Expense", amount: 3667, pct_of_spending: 85.5 },
          { category: "Insurance", type: "Bills & Subscriptions", amount: 620, pct_of_spending: 14.5 },
        ],
      }),
    });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Aug" }));

    expect(await screen.findByRole("img", { name: "Spending by Category, $4,287 total" })).toBeInTheDocument();
  });

  it("totals the Spending by Category card as Expenses plus Bills & Subscriptions, for Full year", async () => {
    respondWith({
      annual: annualWithSpending({
        stat_tiles: { ...ZERO_STAT_TILES, income: 8000, expenses: 6000, bills_subscriptions: 1000 },
        spending_by_category: [
          { category: "Groceries", type: "Expense", amount: 6000, pct_of_spending: 85.7 },
          { category: "Insurance", type: "Bills & Subscriptions", amount: 1000, pct_of_spending: 14.3 },
        ],
      }),
    });
    render(<App />);

    expect(await screen.findByRole("img", { name: "Spending by Category, $7,000 total" })).toBeInTheDocument();
  });

  it("draws a Category in one colour on every card that shows its dot, and Non-Spending rows in their Type colour", async () => {
    respondWith({
      month: monthWithSpending(2026, 8, {
        spending_by_category: [
          { category: "Groceries", type: "Expense", amount: 900, pct_of_spending: 60 },
          { category: "Insurance", type: "Bills & Subscriptions", amount: 600, pct_of_spending: 40 },
        ],
        budgeted_vs_actual: [
          { type: "Expense", category: "Groceries", budgeted: 800, actual: 900, diff: -100, pct: 112.5 },
          { type: "Bills & Subscriptions", category: "Insurance", budgeted: 600, actual: 600, diff: 0, pct: 100 },
          { type: "Debt", category: "Mortgage", budgeted: 2000, actual: 2000, diff: 0, pct: 100 },
        ],
        top_merchants: [{ merchant: "Woolworths", category: "Groceries", total: 900, count: 2 }],
      }),
    });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Aug" }));
    await screen.findByRole("img", { name: /Spending by Category/ });

    const dotColour = (row) => row.querySelector(".dot").style.background;
    const legendRow = (name) => screen.getByText(new RegExp(name), { selector: ".legend__name" }).closest(".legend__row");
    const bvaRow = (name) => screen.getByRole("row", { name: new RegExp(name) });
    const topRow = screen.getByText("Woolworths").closest(".top5__row");

    expect(dotColour(legendRow("Groceries"))).not.toBe(dotColour(legendRow("Insurance")));
    expect(dotColour(bvaRow("Groceries"))).toBe(dotColour(legendRow("Groceries")));
    expect(dotColour(bvaRow("Insurance"))).toBe(dotColour(legendRow("Insurance")));
    expect(topRow.querySelector(".dot").style.background).toBe(dotColour(legendRow("Groceries")));
    expect(dotColour(bvaRow("Mortgage"))).toBe("var(--color-debt)");
  });

  it("gives a Spending Category with no spend this month, but on another card, a palette colour rather than grey", async () => {
    respondWith({
      month: monthWithSpending(2026, 8, {
        spending_by_category: [{ category: "Groceries", type: "Expense", amount: 900, pct_of_spending: 100 }],
        budgeted_vs_actual: [
          { type: "Expense", category: "Groceries", budgeted: 800, actual: 900, diff: -100, pct: 112.5 },
          { type: "Bills & Subscriptions", category: "Gym", budgeted: 40, actual: 0, diff: 40, pct: 0 },
        ],
        recurring_charges: GYM_RECURRING,
      }),
    });
    render(<App />);
    await userEvent.click(await screen.findByRole("button", { name: "Aug" }));
    const recurringRow = (await screen.findByText("Anytime Fitness")).closest("tr");

    const dotColour = (row) => row.querySelector(".dot").style.background;
    const gymBudgetRow = screen.getByText("Gym", { selector: ".bva__row td" }).closest("tr");
    expect(dotColour(recurringRow)).toMatch(/^rgb\(/);
    expect(dotColour(recurringRow)).not.toBe("var(--color-bills-subscriptions)");
    expect(dotColour(gymBudgetRow)).toBe(dotColour(recurringRow));
  });

  it("re-fetches and re-renders every section when the month changes", async () => {
    fetchMock.mockImplementation(async (url) => ({
      ok: true,
      status: 200,
      json: async () => {
        if (url.startsWith("/api/annual-overview")) return annualWithSpending();
        if (url.startsWith("/api/categories")) return [];
        return url.includes("month=9") ? monthOverview({ year: 2026, month: 9 }) : monthWithSpending(2026, 8);
      },
    }));
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "Aug" }));
    expect(await screen.findByText("$5,240")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Sep" }));

    await waitFor(() => expect(screen.getByRole("button", { name: "Sep" })).toHaveAttribute("aria-pressed", "true"));
    expect(fetchMock).toHaveBeenCalledWith("/api/overview?year=2026&month=9", expect.anything());
    await waitFor(() => expect(screen.queryByText("$5,240")).not.toBeInTheDocument());
    expect(screen.queryByText("Woolworths")).not.toBeInTheDocument();
  });

  it("never shows one month's figures under another month's selected pill", async () => {
    // The Aug response is held open, so if the previous month's figures were
    // left on screen they would still be showing under a selected Sep.
    let releaseSeptember;
    const septemberPending = new Promise((resolve) => {
      releaseSeptember = resolve;
    });
    fetchMock.mockImplementation(async (url) => {
      if (url.startsWith("/api/annual-overview")) {
        return { ok: true, status: 200, json: async () => annualWithSpending() };
      }
      if (url.startsWith("/api/categories")) {
        return { ok: true, status: 200, json: async () => [] };
      }
      if (url.includes("month=9")) {
        await septemberPending;
        return { ok: true, status: 200, json: async () => monthOverview({ year: 2026, month: 9 }) };
      }
      return { ok: true, status: 200, json: async () => monthWithSpending(2026, 8) };
    });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "Aug" }));
    expect(await screen.findByText("$5,240")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Sep" }));

    await waitFor(() => expect(screen.queryByText("$5,240")).not.toBeInTheDocument());
    releaseSeptember();
    await waitFor(() => expect(screen.getByRole("heading", { name: "Spending by Category" })).toBeInTheDocument());
  });

  it("renders a month with no Transactions as a coherent empty state, not an error", async () => {
    respondWith({ month: monthOverview({ year: 2026, month: 9 }) });
    render(<App />);
    await screen.findByText("$8,000");

    await userEvent.click(screen.getByRole("button", { name: "Sep" }));

    // Every section is still on the page...
    expect(await screen.findByRole("heading", { name: "Spending by Category" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Budgeted vs Actual" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Spending over time" })).toBeInTheDocument();

    // ...with zeroes and plain empty copy rather than a crash or blank panels.
    expect(screen.getAllByText("$0").length).toBeGreaterThan(0);
    expect(screen.getByText(/No spending recorded for this month/i)).toBeInTheDocument();
    expect(screen.getByText("No spending recorded for this period.")).toBeInTheDocument();
    expect(screen.getByText(/No spending or Category Budgets/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Debt" })).toBeInTheDocument();
    expect(screen.getByText(/No Debt repayments recorded/i)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders the Debt card between Spending by Category/Budgeted vs Actual and Top 5/Spending over time, for a month with Debt", async () => {
    respondWith({
      month: monthWithSpending(2026, 8, {
        stat_tiles: { income: 5240, expenses: 3667, debt: 875, available_to_save: 698, saved: 900, unallocated: -202 },
        debt_summary: [{ notes: "Werribee", amount: 875, pct_of_debt: 100 }],
      }),
    });
    render(<App />);
    await screen.findByText("$8,000");

    await userEvent.click(screen.getByRole("button", { name: "Aug" }));
    await screen.findByText("$5,240");

    const headings = screen.getAllByRole("heading").map((h) => h.textContent);
    expect(headings.indexOf("Budgeted vs Actual")).toBeLessThan(headings.indexOf("Debt"));
    expect(headings.indexOf("Debt")).toBeLessThan(headings.indexOf("Top merchants"));
    expect(screen.getByText("Werribee")).toBeInTheDocument();
    expect(screen.getAllByText("$875").length).toBeGreaterThan(0);
    expect(screen.queryByText(/month average/)).not.toBeInTheDocument();
  });

  it("places the Outflows breakdown full width between the wide-pair row and the split row, for a month", async () => {
    respondWith({
      month: monthWithSpending(2026, 8, {
        stat_tiles: { income: 5240, expenses: 3667, debt: 875, available_to_save: 698, saved: 900, unallocated: -202 },
      }),
    });
    render(<App />);
    await screen.findByText("$8,000");

    await userEvent.click(screen.getByRole("button", { name: "Aug" }));
    await screen.findByText("$5,240");

    const heading = screen.getByRole("heading", { name: "Outflows breakdown" });
    expect(heading.closest(".row--wide-pair")).toBeNull();
    expect(heading.closest(".row--split")).toBeNull();
    const card = heading.closest("section");
    const widePair = screen.getByRole("heading", { name: "Budgeted vs Actual" }).closest(".row--wide-pair");
    expect(widePair.nextElementSibling).toBe(card);
    expect(card.nextElementSibling).toHaveClass("row--split");
  });

  it("groups Spending by Category, Budgeted vs Actual, and Debt into the wide-pair layout, for a month", async () => {
    respondWith({
      month: monthWithSpending(2026, 8, {
        stat_tiles: { income: 5240, expenses: 3667, debt: 875, available_to_save: 698, saved: 900, unallocated: -202 },
        debt_summary: [{ notes: "Werribee", amount: 875, pct_of_debt: 100 }],
      }),
    });
    render(<App />);
    await screen.findByText("$8,000");
    await userEvent.click(screen.getByRole("button", { name: "Aug" }));
    await screen.findByText("$5,240");

    const widePair = screen.getByRole("heading", { name: "Budgeted vs Actual" }).closest(".row--wide-pair");
    expect(widePair).not.toBeNull();
    expect(within(widePair).getByRole("heading", { name: "Spending by Category" })).toBeInTheDocument();
    expect(within(widePair).getByRole("heading", { name: "Debt" })).toBeInTheDocument();
  });

  it("renders the Debt card with a $/month average, for Full year", async () => {
    respondWith({
      annual: annualWithSpending({
        stat_tiles: { income: 8000, expenses: 6000, debt: 1600, available_to_save: 400, saved: 1000, unallocated: -600 },
        monthly_average: { income: 4000, expenses: 3000, debt: 800, available_to_save: 200, saved: 500, unallocated: -300 },
        debt_summary: [{ notes: "Werribee", amount: 1600, pct_of_debt: 100 }],
      }),
    });
    render(<App />);
    await screen.findByText("$8,000");

    const headings = screen.getAllByRole("heading").map((h) => h.textContent);
    expect(headings.indexOf("Month by month")).toBeLessThan(headings.indexOf("Budgeted vs Actual"));
    expect(headings.indexOf("Budgeted vs Actual")).toBeLessThan(headings.indexOf("Debt"));
    expect(screen.getByText("Werribee")).toBeInTheDocument();

    const debtCard = screen.getByRole("heading", { name: "Debt" }).closest("section");
    expect(within(debtCard).getByText("$800 / month average")).toBeInTheDocument();
  });

  it("re-flows Full year into two equal columns, then a row for Top merchants, with no Top Expenses card", async () => {
    respondWith({
      annual: annualWithSpending({
        stat_tiles: { income: 8000, expenses: 6000, debt: 1600, available_to_save: 400, saved: 1000, unallocated: -600 },
        monthly_average: { income: 4000, expenses: 3000, debt: 800, available_to_save: 200, saved: 500, unallocated: -300 },
        debt_summary: [{ notes: "Werribee", amount: 1600, pct_of_debt: 100 }],
        outflows_by_month: ZERO_MONTHS.map((m, index) => (index === 0 ? { ...m, expenses: 600, debt: 400 } : m)),
      }),
    });
    render(<App />);
    await screen.findByText("$8,000");

    const columns =screen.getByRole("heading", { name: "Month by month" }).closest(".row--columns");
    expect(columns).not.toBeNull();
    const [left, right] = columns.querySelectorAll(":scope > .row--columns__col");
    const cardTitles = (column) => [...column.querySelectorAll(":scope > .card h3")].map((h) => h.textContent);
    expect(cardTitles(left)).toEqual(["Month by month", "Spending by Category"]);
    expect(cardTitles(right)).toEqual(["Budgeted vs Actual", "Debt"]);
    expect(columns.closest(".row--wide-pair")).toBeNull();

    const split = screen.getByRole("heading", { name: "Top merchants" }).closest(".row--split");
    expect(split).not.toBeNull();
    // The full-width Outflows breakdown sits between the columns and Top merchants.
    const outflows = screen.getByTestId("outflows-columns-legend").closest("section");
    expect(columns.nextElementSibling).toBe(outflows);
    expect(outflows.nextElementSibling).toBe(split);
    expect(screen.queryByText(/Top \d+ expenses/i)).not.toBeInTheDocument();
  });

  it("draws the Outflows breakdown as stacked columns for Full year, and not for a single month", async () => {
    const months = ZERO_MONTHS.map((m, index) =>
      index === 0 ? { ...m, expenses: 600, bills_subscriptions: 300, debt: 100 } : m,
    );
    respondWith({
      annual: annualWithSpending({ outflows_by_month: months }),
      month: monthWithSpending(2026, 8),
    });
    render(<App />);
    await screen.findByText("$8,000");

    expect(screen.getByRole("img", { name: /Outflows by Type for every month/ })).toBeInTheDocument();
    expect(screen.getByTestId("outflows-columns-legend")).toHaveTextContent("Expenses 60.0%");

    await userEvent.click(screen.getByRole("button", { name: "Aug" }));
    await screen.findByText("$5,240");
    expect(screen.queryByTestId("outflows-columns-legend")).not.toBeInTheDocument();
    expect(screen.queryByRole("img", { name: /Outflows by Type for every month/ })).not.toBeInTheDocument();
  });

  it("places Recurring Charges in the left half of a new bottom row after Top merchants | Spending over time, for a month", async () => {
    respondWith({ month: monthWithSpending(2026, 8, { recurring_charges: GYM_RECURRING }) });
    render(<App />);
    await screen.findByText("$8,000");
    expect(screen.getAllByRole("heading", { name: "Recurring Charges" })).toHaveLength(1);

    await userEvent.click(screen.getByRole("button", { name: "Aug" }));
    await screen.findByText("$5,240");

    const row = screen.getByRole("heading", { name: "Recurring Charges" }).closest(".row--split");
    expect(row).not.toBeNull();
    expect(within(row).queryByRole("heading", { name: "Top merchants" })).not.toBeInTheDocument();
    expect(row.firstElementChild).toContainElement(screen.getByRole("heading", { name: "Recurring Charges" }));
    expect(screen.getByRole("heading", { name: "Top merchants" }).closest(".row--split").nextElementSibling).toBe(row);
    expect(within(row).getByText("Anytime Fitness")).toBeInTheDocument();
    expect(within(row).getByText("$975 / year")).toBeInTheDocument();
  });

  it("places Movers in the right half beside Recurring Charges, for a month, and not at all for Full year", async () => {
    respondWith({
      month: monthWithSpending(2026, 8, { recurring_charges: GYM_RECURRING, movers: DINING_MOVERS }),
      annual: annualWithSpending(),
    });
    render(<App />);
    await screen.findByText("$8,000");
    expect(screen.queryByRole("heading", { name: "Movers" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Aug" }));
    await screen.findByText("$5,240");

    const row = screen.getByRole("heading", { name: "Recurring Charges" }).closest(".row--split");
    const [left, right] = row.children;
    expect(within(left).getByRole("heading", { name: "Recurring Charges" })).toBeInTheDocument();
    expect(within(right).getByRole("heading", { name: "Movers" })).toBeInTheDocument();
    expect(within(right).getByText("vs the average of the preceding 3 months")).toBeInTheDocument();
    expect(within(right).getByText("+$150")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Compare against" }), "previous_month");
    expect(within(right).getByText("+$100")).toBeInTheDocument();
  });

  it("places Recurring Charges beside Top merchants, for Full year", async () => {
    respondWith({ annual: annualWithSpending({ recurring_charges: GYM_RECURRING }) });
    render(<App />);
    await screen.findByText("$8,000");

    const split = screen.getByRole("heading", { name: "Top merchants" }).closest(".row--split");
    const [left, right] = split.children;
    expect(within(left).getByRole("heading", { name: "Top merchants" })).toBeInTheDocument();
    expect(within(right).getByRole("heading", { name: "Recurring Charges" })).toBeInTheDocument();
    expect(within(right).getByText("Fortnightly")).toBeInTheDocument();
  });

  it("shows the Recurring Charges empty state for a view with no Bills & Subscriptions", async () => {
    respondWith({});
    render(<App />);
    await screen.findByText("$8,000");

    expect(screen.getByText(/No Bills & Subscriptions recorded/)).toBeInTheDocument();
  });

  it("shows the ten largest merchants for Full year and five for a month", async () => {
    const merchants = Array.from({ length: 10 }, (_, index) => ({
      merchant: `Merchant ${"ABCDEFGHIJ"[index]}`,
      category: "Groceries",
      total: 1000 - index * 10,
      count: 1,
    }));
    respondWith({
      annual: annualWithSpending({ top_merchants: merchants }),
      month: monthWithSpending(2026, 8, { top_merchants: merchants }),
    });
    render(<App />);
    await screen.findByText("$8,000");

    expect(screen.getAllByText(/^Merchant [A-J]$/)).toHaveLength(10);

    await userEvent.click(screen.getByRole("button", { name: "Aug" }));
    await screen.findByText("$5,240");

    expect(screen.getAllByText(/^Merchant [A-J]$/)).toHaveLength(5);
    expect(screen.queryByText(/Top \d+ expenses/i)).not.toBeInTheDocument();
  });

  it("surfaces a backend failure instead of rendering a half-empty page", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/500/);
  });

  it("opens the Recurring Transactions Config screen from the Settings tab", async () => {
    routeTo({ "/api/annual-overview": annualWithSpending(), "/api/recurring-rules": [], "/api/categories": [] });
    render(<App />);
    expect(await screen.findByText("$8,000")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Settings" }));

    expect(await screen.findByRole("heading", { name: "Recurring Transactions" })).toBeInTheDocument();
    expect(screen.getByText("Settings")).toHaveAttribute("aria-current", "page");
  });

  it("puts the Overview's month selector away while Settings is open", async () => {
    routeTo({ "/api/annual-overview": annualWithSpending(), "/api/recurring-rules": [], "/api/categories": [] });
    render(<App />);
    expect(await screen.findByText("$8,000")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Settings" }));

    // The month selector picks a month for the Overview - it means nothing here.
    await waitFor(() => expect(screen.queryByRole("group", { name: "Select month" })).not.toBeInTheDocument());
    expect(screen.queryByText("$8,000")).not.toBeInTheDocument();
  });

  it("comes back to the Overview with its month still selected", async () => {
    routeTo({
      "/api/annual-overview": annualWithSpending(),
      "/api/overview": monthWithSpending(2026, 8),
      "/api/recurring-rules": [],
      "/api/categories": [],
    });
    render(<App />);
    expect(await screen.findByText("$8,000")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Aug" }));
    expect(await screen.findByText("$5,240")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    await screen.findByRole("heading", { name: "Recurring Transactions" });
    await userEvent.click(screen.getByRole("button", { name: "Overview" }));

    expect(await screen.findByText("$5,240")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aug" })).toHaveAttribute("aria-pressed", "true");
  });

  it("opens the Budget tab's per-month editor from the Budget tab", async () => {
    routeTo({
      "/api/annual-overview": annualWithSpending(),
      "/api/budget-editor": { Income: [{ category: "Salary", amount: null }], Expense: [], Debt: [] },
    });
    render(<App />);
    expect(await screen.findByText("$8,000")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Budget" }));

    expect(await screen.findByRole("heading", { name: "Budget" })).toBeInTheDocument();
    expect(screen.getByText("Salary")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Budget" })).toHaveAttribute("aria-current", "page");
  });

  it("keeps Budget's own pill selection across a tab switch, the same way Overview's persists", async () => {
    routeTo({
      "/api/annual-overview": annualWithSpending(),
      "/api/budget-editor": { Income: [{ category: "Salary", amount: null }], Expense: [], Debt: [] },
      "/api/budget-grid": { Income: [], Expense: [], Debt: [] },
      "/api/budget-suggestion": { write_up: null, generated_at: null },
      "/api/categories": [],
      "/api/recurring-rules": [],
    });
    render(<App />);
    expect(await screen.findByText("$8,000")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Budget" }));
    await screen.findByText("Salary");
    await userEvent.click(screen.getByRole("button", { name: "Full year" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Full year" })).toHaveAttribute("aria-pressed", "true"));

    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    await userEvent.click(screen.getByRole("button", { name: "Budget" }));

    expect(await screen.findByRole("button", { name: "Full year" })).toHaveAttribute("aria-pressed", "true");
  });

  it("opens the Transactions tab and lists that Financial Year's Transactions newest-first", async () => {
    routeTo({
      "/api/annual-overview": annualWithSpending(),
      "/api/transactions": [
        { id: 1, date: "2026-08-01", amount: 42.5, type: "Expense", category: "Groceries", notes: "Woolworths" },
        { id: 2, date: "2027-02-01", amount: 4000, type: "Income", category: "Salary", notes: "Employer" },
      ],
      "/api/categories": [],
    });
    render(<App />);
    expect(await screen.findByText("$8,000")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Transactions" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/transactions?year=2026&month=7", expect.anything()),
    );
    expect(await screen.findByRole("heading", { name: "Transactions" })).toBeInTheDocument();
    expect(screen.getByText("Employer")).toBeInTheDocument();
    expect(screen.getByText("Woolworths")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Transactions" })).toHaveAttribute("aria-current", "page");
  });

  it("dates the page by the newest Transaction in the log, not by today", async () => {
    // The clock says 21 August; the Transaction Log only runs to the 3rd.
    respondWith({ latestTransactionDate: "2026-08-03" });
    render(<App />);

    expect(await screen.findByText("As at 3 August")).toBeInTheDocument();
    expect(screen.queryByText("As at 21 August")).not.toBeInTheDocument();
  });

  it("keeps the As at date still when the reader switches months", async () => {
    respondWith();
    render(<App />);
    expect(await screen.findByText("As at 3 August")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Sep" }));

    await waitFor(() => expect(screen.getByRole("button", { name: "Sep" })).toHaveAttribute("aria-pressed", "true"));
    expect(screen.getByText("As at 3 August")).toBeInTheDocument();
  });

  it("says nothing about a date when the Transaction Log is empty", async () => {
    respondWith({ latestTransactionDate: null });
    render(<App />);

    await screen.findByRole("heading", { name: "Where did my income go?" });
    expect(screen.queryByText(/^As at/)).not.toBeInTheDocument();
  });

  it("shows the nav tabs, with only Overview marked current", async () => {
    respondWith();
    render(<App />);

    const nav = await screen.findByRole("navigation");

    expect(within(nav).getByText("Transactions")).toBeInTheDocument();
    expect(within(nav).getByText("Budget")).toBeInTheDocument();
    expect(within(nav).getByText("Settings")).toBeInTheDocument();
    expect(within(nav).getByText("Overview")).toHaveAttribute("aria-current", "page");
  });

  describe("Financial Year/Calendar Year switcher", () => {
    it("renders above the nav, and hides on the Settings tab", async () => {
      routeTo({
        "/api/annual-overview": annualWithSpending(),
        "/api/transaction-date-range": { earliest: "2025-12-17", latest: "2026-08-03" },
        "/api/recurring-rules": [],
        "/api/categories": [],
      });
      render(<App />);
      await screen.findByText("$8,000");

      expect(screen.getByRole("group", { name: "Select year" })).toBeInTheDocument();
      expect(screen.getByRole("group", { name: "Financial Year or Calendar Year" })).toBeInTheDocument();

      await userEvent.click(screen.getByRole("button", { name: "Settings" }));

      expect(screen.queryByRole("group", { name: "Select year" })).not.toBeInTheDocument();
    });

    it("disables the Next arrow at the Financial Year containing today", async () => {
      respondWith();
      render(<App />);
      await screen.findByText("$8,000");

      expect(screen.getByRole("button", { name: "Next year" })).toBeDisabled();
    });

    it("disables the Previous arrow at the Financial Year containing the earliest Transaction", async () => {
      respondWith();
      render(<App />);
      await screen.findByText("$8,000");

      await userEvent.click(screen.getByRole("button", { name: "Previous year" }));
      await screen.findByText("2025-2026 Financial Year");

      expect(screen.getByRole("button", { name: "Previous year" })).toBeDisabled();
    });

    it("steps back a Financial Year with the Previous arrow, refetching Full year for it", async () => {
      respondWith();
      render(<App />);
      await screen.findByText("$8,000");

      await userEvent.click(screen.getByRole("button", { name: "Previous year" }));

      await waitFor(() =>
        expect(fetchMock).toHaveBeenCalledWith("/api/annual-overview?year=2025&period=financial", expect.anything()),
      );
      expect(await screen.findByText("2025-2026 Financial Year")).toBeInTheDocument();
    });

    it("resets to Full year when a year arrow is used while a month is selected", async () => {
      respondWith();
      render(<App />);
      await screen.findByText("$8,000");
      await userEvent.click(screen.getByRole("button", { name: "Aug" }));
      await screen.findByText("$5,240");

      await userEvent.click(screen.getByRole("button", { name: "Previous year" }));

      await waitFor(() =>
        expect(screen.getByRole("button", { name: "Full year" })).toHaveAttribute("aria-pressed", "true"),
      );
      // Full year's own sections show, not Aug's per-month-only ones.
      expect(await screen.findByRole("heading", { name: "Month by month" })).toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "Spending over time" })).not.toBeInTheDocument();
    });

    it("switches to Calendar Year framing, relabelling the header and reordering the month pills", async () => {
      respondWith();
      render(<App />);
      await screen.findByText("$8,000");

      await userEvent.click(screen.getByRole("button", { name: "Calendar Year" }));

      expect(await screen.findByText("Calendar Year 2026")).toBeInTheDocument();
      await waitFor(() =>
        expect(fetchMock).toHaveBeenCalledWith("/api/annual-overview?year=2026&period=calendar", expect.anything()),
      );
      const pills = screen.getByRole("group", { name: "Select month" });
      const labels = within(pills)
        .getAllByRole("button")
        .map((pill) => pill.textContent);
      expect(labels).toEqual(["Full year", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]);
    });

    it("keeps a selected month anchored to the same real month when framing is toggled", async () => {
      respondWith();
      render(<App />);
      await screen.findByText("$8,000");
      await userEvent.click(screen.getByRole("button", { name: "Aug" }));
      await screen.findByText("$5,240");

      await userEvent.click(screen.getByRole("button", { name: "Calendar Year" }));

      expect(await screen.findByText("Calendar Year 2026")).toBeInTheDocument();
      expect(await screen.findByText("$5,240")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Aug" })).toHaveAttribute("aria-pressed", "true");
    });

    it("falls back to the period containing today when the toggle is flipped while Full year is selected", async () => {
      respondWith();
      render(<App />);
      await screen.findByText("$8,000");
      await userEvent.click(screen.getByRole("button", { name: "Previous year" }));
      await screen.findByText("2025-2026 Financial Year");

      await userEvent.click(screen.getByRole("button", { name: "Calendar Year" }));

      expect(await screen.findByText("Calendar Year 2026")).toBeInTheDocument();
    });

    it("persists periodType across a reload, but resets referenceYear to the current period", async () => {
      respondWith();
      const { unmount } = render(<App />);
      await screen.findByText("$8,000");

      await userEvent.click(screen.getByRole("button", { name: "Calendar Year" }));
      await screen.findByText("Calendar Year 2026");
      await userEvent.click(screen.getByRole("button", { name: "Previous year" }));
      await screen.findByText("Calendar Year 2025");

      unmount();
      render(<App />);

      expect(await screen.findByText("Calendar Year 2026")).toBeInTheDocument();
    });
  });

  describe("Financial Year/Calendar Year switcher on the Budget tab", () => {
    // Layers Budget's own endpoints (its Category Budget editor, Full year
    // grid, write-up, and Category list) onto respondWith's Overview
    // defaults, since App always mounts on the Overview tab first.
    function respondWithBudget({
      grid = { Income: [], Expense: [], Debt: [] },
      editor = { Income: [{ category: "Salary", amount: null }], Expense: [], Debt: [] },
    } = {}) {
      respondWith({
        extra: {
          "/api/budget-editor": editor,
          "/api/budget-grid": grid,
          "/api/budget-suggestion": { write_up: null, generated_at: null },
          "/api/categories": [],
        },
      });
    }

    it("reorders Budget's month pills Jan→Dec when Calendar Year is active, matching Overview", async () => {
      respondWithBudget();
      render(<App />);
      await screen.findByText("$8,000");
      await userEvent.click(screen.getByRole("button", { name: "Budget" }));
      await screen.findByText("Salary");

      await userEvent.click(screen.getByRole("button", { name: "Calendar Year" }));

      await screen.findByText("Calendar Year 2026");
      const pills = screen.getByRole("group", { name: "Select month" });
      const labels = within(pills)
        .getAllByRole("button")
        .map((pill) => pill.textContent);
      expect(labels).toEqual(["Full year", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]);
    });

    it("requests Budget's Full year grid for the shared referenceYear and period", async () => {
      respondWithBudget();
      render(<App />);
      await screen.findByText("$8,000");
      await userEvent.click(screen.getByRole("button", { name: "Budget" }));
      await screen.findByText("Salary");

      await userEvent.click(screen.getByRole("button", { name: "Full year" }));

      await waitFor(() =>
        expect(fetchMock).toHaveBeenCalledWith("/api/budget-grid?year=2026&period=financial", expect.anything()),
      );
    });

    it("steps back a year with the Previous arrow while on the Budget tab, resetting to Full year and refetching its grid", async () => {
      respondWithBudget();
      render(<App />);
      await screen.findByText("$8,000");
      await userEvent.click(screen.getByRole("button", { name: "Budget" }));
      await screen.findByText("Salary");

      await userEvent.click(screen.getByRole("button", { name: "Previous year" }));

      expect(await screen.findByText("2025-2026 Financial Year")).toBeInTheDocument();
      await waitFor(() =>
        expect(screen.getByRole("button", { name: "Full year" })).toHaveAttribute("aria-pressed", "true"),
      );
      await waitFor(() =>
        expect(fetchMock).toHaveBeenCalledWith("/api/budget-grid?year=2025&period=financial", expect.anything()),
      );
    });

    it("keeps Budget's selected month anchored when the toggle is flipped while on the Budget tab", async () => {
      respondWithBudget();
      render(<App />);
      await screen.findByText("$8,000");
      await userEvent.click(screen.getByRole("button", { name: "Budget" }));
      await screen.findByText("Salary");
      expect(screen.getByRole("button", { name: "Aug" })).toHaveAttribute("aria-pressed", "true");

      await userEvent.click(screen.getByRole("button", { name: "Calendar Year" }));

      expect(await screen.findByText("Calendar Year 2026")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Aug" })).toHaveAttribute("aria-pressed", "true");
      expect(screen.getByText("Salary")).toBeInTheDocument();
    });

    it("does not disturb Overview's own selected month when the year arrow is used on the Budget tab", async () => {
      respondWithBudget();
      render(<App />);
      await screen.findByText("$8,000");
      await userEvent.click(screen.getByRole("button", { name: "Aug" }));
      await screen.findByText("$5,240");

      await userEvent.click(screen.getByRole("button", { name: "Budget" }));
      await screen.findByText("Salary");
      await userEvent.click(screen.getByRole("button", { name: "Previous year" }));
      await screen.findByText("2025-2026 Financial Year");

      await userEvent.click(screen.getByRole("button", { name: "Overview" }));

      // Overview's own selected month is untouched by a year-arrow click made
      // while Budget was the active tab (ADR-0021: each tab's own
      // month/Full-year selection is independent) - it still shows Aug's own
      // figures, not Full year's.
      expect(await screen.findByText("$5,240")).toBeInTheDocument();
    });
  });

  describe("Financial Year/Calendar Year switcher on the Transactions tab", () => {
    // Layers Transactions' own endpoints onto respondWith's Overview
    // defaults, since App always mounts on the Overview tab first.
    function respondWithTransactions({
      transactions = [
        { id: 1, date: "2026-08-01", amount: 42.5, type: "Expense", category: "Groceries", notes: "Woolworths" },
      ],
    } = {}) {
      respondWith({
        extra: {
          "/api/transactions": transactions,
          "/api/categories": [],
        },
      });
    }

    it("requests Transactions for the shared referenceYear and start month - Jul for Financial Year, Jan for Calendar Year", async () => {
      respondWithTransactions();
      render(<App />);
      await screen.findByText("$8,000");
      await userEvent.click(screen.getByRole("button", { name: "Transactions" }));
      await waitFor(() =>
        expect(fetchMock).toHaveBeenCalledWith("/api/transactions?year=2026&month=7", expect.anything()),
      );

      await userEvent.click(screen.getByRole("button", { name: "Calendar Year" }));

      await screen.findByText("Calendar Year 2026");
      await waitFor(() =>
        expect(fetchMock).toHaveBeenCalledWith("/api/transactions?year=2026&month=1", expect.anything()),
      );
    });

    it("reorders Transactions' month filter Jan→Dec when Calendar Year is active, matching Overview/Budget", async () => {
      respondWithTransactions();
      render(<App />);
      await screen.findByText("$8,000");
      await userEvent.click(screen.getByRole("button", { name: "Transactions" }));
      await screen.findByText("Woolworths");

      await userEvent.click(screen.getByRole("button", { name: "Calendar Year" }));
      await screen.findByText("Calendar Year 2026");

      const options = within(screen.getByLabelText("Month"))
        .getAllByRole("option")
        .map((option) => option.textContent);
      expect(options).toEqual([
        "All months",
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
      ]);
    });

    it("steps back a year with the Previous arrow while on the Transactions tab, refetching for that year", async () => {
      respondWithTransactions();
      render(<App />);
      await screen.findByText("$8,000");
      await userEvent.click(screen.getByRole("button", { name: "Transactions" }));
      await screen.findByText("Woolworths");

      await userEvent.click(screen.getByRole("button", { name: "Previous year" }));

      expect(await screen.findByText("2025-2026 Financial Year")).toBeInTheDocument();
      await waitFor(() =>
        expect(fetchMock).toHaveBeenCalledWith("/api/transactions?year=2025&month=7", expect.anything()),
      );
    });

    it("the Export panel's default date range follows the shared switcher on the Transactions tab", async () => {
      respondWithTransactions();
      render(<App />);
      await screen.findByText("$8,000");
      await userEvent.click(screen.getByRole("button", { name: "Transactions" }));
      await screen.findByText("Woolworths");
      await userEvent.click(screen.getByRole("button", { name: "Calendar Year" }));
      await screen.findByText("Calendar Year 2026");

      await userEvent.click(screen.getByRole("button", { name: "More options" }));
      await userEvent.click(screen.getByRole("menuitem", { name: "Export transactions" }));

      expect(screen.getByLabelText("Start date")).toHaveValue("2026-01-01");
      expect(screen.getByLabelText("End date")).toHaveValue("2026-12-31");
    });

    it("does not disturb Overview's own selected month when the toggle or year arrow is used on the Transactions tab", async () => {
      respondWithTransactions();
      render(<App />);
      await screen.findByText("$8,000");
      await userEvent.click(screen.getByRole("button", { name: "Aug" }));
      await screen.findByText("$5,240");

      await userEvent.click(screen.getByRole("button", { name: "Transactions" }));
      await screen.findByText("Woolworths");
      await userEvent.click(screen.getByRole("button", { name: "Previous year" }));
      await screen.findByText("2025-2026 Financial Year");
      await userEvent.click(screen.getByRole("button", { name: "Calendar Year" }));
      await screen.findByText("Calendar Year 2026");

      await userEvent.click(screen.getByRole("button", { name: "Overview" }));

      // Overview's own selected month is untouched by a toggle/year-arrow
      // click made while Transactions was the active tab (ADR-0021: each
      // tab's own month/Full-year selection is independent, and
      // Transactions owns none of its own to reset) - it still shows Aug's
      // own figures, not Full year's.
      expect(await screen.findByText("$5,240")).toBeInTheDocument();
    });
  });
});

describe("Display Currency setting", () => {
  const DEFAULT_SETTINGS = { currency: "AUD", financial_year_start_month: 7, date_order: "day-first" };
  const NBSP = " ";
  const EURO_OPTION = `EUR - 1.234,56${NBSP}€`;

  // The settings endpoint as the real server behaves: a GET reads what was
  // last saved, a PUT merges the body in and answers with everything.
  function respondWithSettings(saved = {}, { transactions = [], rules = [], extra = {} } = {}) {
    let settings = { ...DEFAULT_SETTINGS, ...saved };
    const bodies = {
      "/api/annual-overview": annualWithSpending(),
      "/api/overview": monthWithSpending(2026, 8),
      "/api/latest-transaction-date": { date: "2026-08-03" },
      "/api/transaction-date-range": { earliest: "2025-12-17", latest: "2026-08-03" },
      "/api/transactions": transactions,
      "/api/recurring-rules": rules,
      "/api/categories": [],
      ...extra,
    };
    fetchMock.mockImplementation(async (url, options = {}) => {
      if (url.startsWith("/api/settings")) {
        if (options.method === "PUT") {
          settings = { ...settings, ...JSON.parse(options.body) };
        }
        return { ok: true, status: 200, json: async () => settings };
      }
      const match = Object.keys(bodies).find((path) => url.startsWith(path));
      return { ok: true, status: 200, json: async () => bodies[match] };
    });
  }

  async function chooseCurrency(value) {
    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    await userEvent.selectOptions(await screen.findByRole("combobox", { name: "Display Currency" }), value);
    await userEvent.click(screen.getByRole("button", { name: "Save settings" }));
  }

  it("shows every amount in Australian dollars when no setting has ever been saved", async () => {
    respondWithSettings();
    render(<App />);

    expect(await screen.findByText("$8,000")).toBeInTheDocument();
  });

  it("falls back to Australian dollars when the settings can't be read", async () => {
    // No /api/settings route at all: the stub answers with an empty body.
    respondWith();
    render(<App />);

    expect(await screen.findByText("$8,000")).toBeInTheDocument();
  });

  it("offers a dropdown of currencies, each with a sample of its format, and says changing it relabels and never converts", async () => {
    respondWithSettings();
    render(<App />);
    await screen.findByText("$8,000");

    await userEvent.click(screen.getByRole("button", { name: "Settings" }));

    const dropdown = await screen.findByRole("combobox", { name: "Display Currency" });
    expect(dropdown).toHaveValue("AUD");
    expect(within(dropdown).getByRole("option", { name: "AUD - $1,234.56" })).toBeInTheDocument();
    // One euro entry, not one per country.
    expect(within(dropdown).getAllByRole("option", { name: /^EUR/ })).toHaveLength(1);
    expect(within(dropdown).getByRole("option", { name: EURO_OPTION })).toBeInTheDocument();
    expect(within(dropdown).getByRole("option", { name: "JPY - ¥1,235" })).toBeInTheDocument();
    expect(screen.getByText(/relabels existing amounts and never converts them/i)).toBeInTheDocument();
  });

  it("saves the chosen currency to the settings endpoint", async () => {
    respondWithSettings();
    render(<App />);
    await screen.findByText("$8,000");

    await chooseCurrency("EUR");

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/settings",
        expect.objectContaining({ method: "PUT", body: JSON.stringify({ currency: "EUR" }) }),
      ),
    );
  });

  it("re-renders the Overview in a comma-decimal euro convention as soon as it is saved, with no $ left", async () => {
    respondWithSettings();
    render(<App />);
    await screen.findByText("$8,000");
    await chooseCurrency("EUR");

    await userEvent.click(screen.getByRole("button", { name: "Overview" }));

    expect(await screen.findByText(`8.000 €`)).toBeInTheDocument(); // Real Income tile
    expect(screen.getByText(`4.000 € / month average`)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("$");
  });

  it("starts up already showing the saved currency", async () => {
    respondWithSettings({ currency: "GBP" });
    render(<App />);

    expect(await screen.findByText("£8,000")).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("$");
  });

  it("shows a month's amounts and signed differences in the chosen currency", async () => {
    respondWithSettings({ currency: "EUR" });
    render(<App />);
    await screen.findByText(`8.000 €`);

    await userEvent.click(screen.getByRole("button", { name: "Aug" }));

    expect(await screen.findByText(`5.240 €`)).toBeInTheDocument(); // Real Income tile
    expect(screen.getAllByText(`+3.017 €`).length).toBeGreaterThan(0); // Budgeted vs Actual overspend, signed
    expect(document.body.textContent).not.toContain("$");
  });

  it("shows Transactions' and Recurring rules' precise amounts with the currency's own decimals", async () => {
    respondWithSettings(
      { currency: "EUR" },
      {
        transactions: [
          { id: 1, date: "2026-08-01", amount: 1234.56, type: "Expense", category: "Groceries", notes: "Woolworths" },
        ],
        rules: [
          {
            id: 1,
            amount: 1234.56,
            type: "Expense",
            category: "Entertainment & Leisure",
            notes: "Streaming service",
            frequency: "Weekly",
            interval: 1,
            day: "Wednesday",
            start_date: "2026-08-05",
            end_date: null,
          },
        ],
      },
    );
    render(<App />);
    await screen.findByText(`8.000 €`);

    await userEvent.click(screen.getByRole("button", { name: "Transactions" }));
    expect(await screen.findByText(`1.234,56 €`)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("$");

    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    expect(await screen.findByText(`1.234,56 €`)).toBeInTheDocument();
    // Scoped to the Recurring section: the currency picker above it samples $ for the dollar entries.
    const recurring = screen.getByRole("heading", { name: "Recurring Transactions" }).closest("section");
    expect(recurring.textContent).not.toContain("$");
  });

  it("shows yen without decimal places, including precise amounts", async () => {
    respondWithSettings(
      { currency: "JPY" },
      {
        transactions: [
          { id: 1, date: "2026-08-01", amount: 1234.56, type: "Expense", category: "Groceries", notes: "Woolworths" },
        ],
      },
    );
    render(<App />);
    expect(await screen.findByText("¥8,000")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Transactions" }));

    expect(await screen.findByText("¥1,235")).toBeInTheDocument();
    expect(screen.queryByText(/\.\d\d/)).not.toBeInTheDocument();
  });

  it("shows the Budget tab's editor, Type Totals and Full year grid in the chosen currency too", async () => {
    const editorRow = {
      category: "Groceries",
      amount: 650,
      last_month_actual: 620,
      last_month_budgeted: 600,
      trailing_average_actual: 590,
      average_variance_pct: 12.3,
      month_actual: 306,
    };
    respondWithSettings(
      { currency: "EUR" },
      {
        extra: {
          "/api/budget-editor": { Income: [], Expense: [editorRow], Debt: [] },
          "/api/budget-grid": {
            Income: [],
            Expense: [{ category: "Groceries", amounts: [650, ...Array(11).fill(null)] }],
            Debt: [],
          },
          "/api/budget-suggestion": { write_up: null, generated_at: null },
        },
      },
    );
    render(<App />);
    await screen.findByText(`8.000 €`);

    await userEvent.click(screen.getByRole("button", { name: "Budget" }));
    expect(await screen.findByText(`620 €`)).toBeInTheDocument(); // Last month actual
    expect(document.body.textContent).not.toContain("$");

    await userEvent.click(screen.getByRole("button", { name: "Full year" }));
    expect(await screen.findAllByText(`650 €`)).not.toHaveLength(0);
    expect(document.body.textContent).not.toContain("$");
  });

  describe("as one Display Settings tile", () => {
    async function openSettings() {
      respondWithSettings();
      render(<App />);
      await screen.findByText("$8,000");
      await userEvent.click(screen.getByRole("button", { name: "Settings" }));
      await screen.findByRole("combobox", { name: "Display Currency" });
    }

    function putBodies() {
      return fetchMock.mock.calls
        .filter(([url, options]) => url === "/api/settings" && options?.method === "PUT")
        .map(([, options]) => JSON.parse(options.body));
    }

    it("holds the currency, Financial Year start and Date Order together under one 'Display Settings' heading", async () => {
      await openSettings();

      const tile = screen.getByRole("heading", { name: "Display Settings" }).closest("section");
      expect(within(tile).getByRole("combobox", { name: "Display Currency" })).toBeInTheDocument();
      expect(within(tile).getByRole("combobox", { name: "Financial Year start month" })).toBeInTheDocument();
      expect(within(tile).getByRole("combobox", { name: "Date Order" })).toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "Display Currency" })).not.toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "Date Order" })).not.toBeInTheDocument();
      expect(screen.queryByRole("heading", { name: "Financial Year" })).not.toBeInTheDocument();
    });

    it("has one Save button, disabled until something changes", async () => {
      await openSettings();

      expect(screen.getAllByRole("button", { name: /^Save/ })).toHaveLength(1);
      const save = screen.getByRole("button", { name: "Save settings" });
      expect(save).toBeDisabled();

      await userEvent.selectOptions(screen.getByRole("combobox", { name: "Date Order" }), "month-first");
      expect(save).toBeEnabled();

      await userEvent.selectOptions(screen.getByRole("combobox", { name: "Date Order" }), "day-first");
      expect(save).toBeDisabled();
    });

    it("saves every changed setting in one request, and only the changed ones", async () => {
      await openSettings();

      await userEvent.selectOptions(screen.getByRole("combobox", { name: "Display Currency" }), "GBP");
      await userEvent.selectOptions(screen.getByRole("combobox", { name: "Date Order" }), "month-first");
      await userEvent.click(screen.getByRole("button", { name: "Save settings" }));

      await waitFor(() => expect(putBodies()).toEqual([{ currency: "GBP", date_order: "month-first" }]));
      await waitFor(() => expect(screen.getByRole("button", { name: "Save settings" })).toBeDisabled()); // now saved

      await userEvent.click(screen.getByRole("button", { name: "Overview" }));
      expect(await screen.findByText("£8,000")).toBeInTheDocument();
      expect(screen.getByText("As at August 3")).toBeInTheDocument(); // month-first (latest Transaction is 3 Aug)
    });

    it("shows the server's refusal and leaves the choices in place", async () => {
      await openSettings();
      fetchMock.mockImplementationOnce(async () => ({
        ok: false,
        status: 400,
        json: async () => ({ error: "currency 'XXX' is not an available Display Currency" }),
      }));

      await userEvent.selectOptions(screen.getByRole("combobox", { name: "Display Currency" }), "GBP");
      await userEvent.click(screen.getByRole("button", { name: "Save settings" }));

      expect(await screen.findByRole("alert")).toHaveTextContent("not an available Display Currency");
      expect(screen.getByRole("combobox", { name: "Display Currency" })).toHaveValue("GBP");
    });
  });
});

describe("Date Order setting", () => {
  const DEFAULT_SETTINGS = { currency: "AUD", financial_year_start_month: 7, date_order: "day-first" };

  // The settings endpoint as the real server behaves: a GET reads what was
  // last saved, a PUT merges the body in and answers with everything.
  function respondWithSettings(saved = {}) {
    let settings = { ...DEFAULT_SETTINGS, ...saved };
    const bodies = {
      "/api/annual-overview": annualWithSpending(),
      "/api/overview": monthWithSpending(2026, 8),
      "/api/latest-transaction-date": { date: "2026-08-19" },
      "/api/transaction-date-range": { earliest: "2025-12-17", latest: "2026-08-19" },
      "/api/transactions": [],
      "/api/recurring-rules": [],
      "/api/categories": [],
      "/api/budget-editor": { Income: [], Expense: [], Debt: [] },
      "/api/budget-grid": { Income: [], Expense: [], Debt: [] },
      "/api/budget-suggestion": { write_up: "- Trim groceries", generated_at: "2026-08-20T14:32:00" },
    };
    fetchMock.mockImplementation(async (url, options = {}) => {
      if (url.startsWith("/api/settings")) {
        if (options.method === "PUT") {
          settings = { ...settings, ...JSON.parse(options.body) };
        }
        return { ok: true, status: 200, json: async () => settings };
      }
      const match = Object.keys(bodies).find((path) => url.startsWith(path));
      return { ok: true, status: 200, json: async () => bodies[match] };
    });
  }

  async function chooseDateOrder(value) {
    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    await userEvent.selectOptions(await screen.findByRole("combobox", { name: "Date Order" }), value);
    await userEvent.click(screen.getByRole("button", { name: "Save settings" }));
  }

  it("writes dates day-first everywhere when no Date Order has ever been saved", async () => {
    respondWithSettings();
    render(<App />);

    expect(await screen.findByText("As at 19 August")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Aug" }));
    expect(await screen.findByText("1 Aug")).toBeInTheDocument(); // Spending Over Time axis

    await userEvent.click(screen.getByRole("button", { name: "Budget" }));
    expect(await screen.findByText("Generated 20 Aug 2026, 2:32pm")).toBeInTheDocument();
  });

  it("offers day-first and month-first in Settings, saved through the settings endpoint", async () => {
    respondWithSettings();
    render(<App />);
    await screen.findByText("As at 19 August");

    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    const dropdown = await screen.findByRole("combobox", { name: "Date Order" });
    expect(dropdown).toHaveValue("day-first");
    expect(within(dropdown).getByRole("option", { name: "Day first (19 Aug)" })).toBeInTheDocument();
    expect(within(dropdown).getByRole("option", { name: "Month first (Aug 19)" })).toBeInTheDocument();

    await chooseDateOrder("month-first");

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/settings",
        expect.objectContaining({ method: "PUT", body: JSON.stringify({ date_order: "month-first" }) }),
      ),
    );
  });

  it("flips the As at header, the Spending Over Time axis and the Budget Suggestion time to month-first as soon as it is saved, with English month names", async () => {
    respondWithSettings();
    render(<App />);
    await screen.findByText("As at 19 August");

    await chooseDateOrder("month-first");

    expect(await screen.findByText("As at August 19")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Overview" }));
    await userEvent.click(await screen.findByRole("button", { name: "Aug" }));
    expect(await screen.findByText("Aug 1")).toBeInTheDocument();
    expect(screen.queryByText("1 Aug")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Budget" }));
    expect(await screen.findByText("Generated Aug 20, 2026, 2:32pm")).toBeInTheDocument();
  });

  it("flips back to day-first when day-first is chosen again", async () => {
    respondWithSettings({ date_order: "month-first" });
    render(<App />);
    expect(await screen.findByText("As at August 19")).toBeInTheDocument();

    await chooseDateOrder("day-first");

    expect(await screen.findByText("As at 19 August")).toBeInTheDocument();
  });

  it("starts up already writing dates in the saved order", async () => {
    respondWithSettings({ date_order: "month-first" });
    render(<App />);

    expect(await screen.findByText("As at August 19")).toBeInTheDocument();
  });
});

describe("Financial Year start month setting", () => {
  const DEFAULT_SETTINGS = { currency: "AUD", financial_year_start_month: 7, date_order: "day-first" };
  const FULL_YEAR_THEN = (months) => ["Full year", ...months];
  const APR_TO_MAR = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"];
  const JAN_TO_DEC = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const JUL_TO_JUN = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"];

  // The settings endpoint as the real server behaves (see the Display
  // Currency tests): a GET reads what was last saved, a PUT merges and answers
  // with everything.
  function respondWithStartMonth(startMonth, { earliest = "2025-12-17", extra = {} } = {}) {
    let settings = { ...DEFAULT_SETTINGS, financial_year_start_month: startMonth };
    const bodies = {
      "/api/annual-overview": annualWithSpending(),
      "/api/overview": monthWithSpending(2026, 8),
      "/api/latest-transaction-date": { date: "2026-08-03" },
      "/api/transaction-date-range": { earliest, latest: "2026-08-03" },
      "/api/transactions": [
        { id: 1, date: "2026-08-01", amount: 42.5, type: "Expense", category: "Groceries", notes: "Woolworths" },
      ],
      "/api/recurring-rules": [],
      "/api/categories": [],
      "/api/budget-editor": { Income: [{ category: "Salary", amount: null }], Expense: [], Debt: [] },
      "/api/budget-grid": { Income: [{ category: "Salary", amounts: Array(12).fill(null) }], Expense: [], Debt: [] },
      "/api/budget-suggestion": { write_up: null, generated_at: null },
      ...extra,
    };
    fetchMock.mockImplementation(async (url, options = {}) => {
      if (url.startsWith("/api/settings")) {
        if (options.method === "PUT") {
          settings = { ...settings, ...JSON.parse(options.body) };
        }
        return { ok: true, status: 200, json: async () => settings };
      }
      const match = Object.keys(bodies).find((path) => url.startsWith(path));
      return { ok: true, status: 200, json: async () => bodies[match] };
    });
  }

  function pillLabels() {
    return within(screen.getByRole("group", { name: "Select month" }))
      .getAllByRole("button")
      .map((pill) => pill.textContent);
  }

  it("behaves exactly as before - July to June - when no start month has been saved", async () => {
    respondWithStartMonth(7);
    render(<App />);

    expect(await screen.findByText("2026-2027 Financial Year")).toBeInTheDocument();
    expect(pillLabels()).toEqual(FULL_YEAR_THEN(JUL_TO_JUN));
    expect(screen.getByRole("group", { name: "Financial Year or Calendar Year" })).toBeInTheDocument();
  });

  it("orders the Overview's month pills April to March for an April start, labelled 2026-2027", async () => {
    respondWithStartMonth(4);
    render(<App />);

    expect(await screen.findByText("2026-2027 Financial Year")).toBeInTheDocument();
    expect(pillLabels()).toEqual(FULL_YEAR_THEN(APR_TO_MAR));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/annual-overview?year=2026&period=financial", expect.anything()),
    );
  });

  it("names the Financial Year containing today by the saved start month", async () => {
    // 21 August 2026 falls in the October-start year that began in October 2025.
    respondWithStartMonth(10);
    render(<App />);

    expect(await screen.findByText("2025-2026 Financial Year")).toBeInTheDocument();
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/annual-overview?year=2025&period=financial", expect.anything()),
    );
  });

  it("orders the Budget tab's pills and Full year grid April to March for an April start", async () => {
    respondWithStartMonth(4);
    render(<App />);
    await screen.findByText("$8,000");
    await userEvent.click(screen.getByRole("button", { name: "Budget" }));
    await screen.findByText("Salary");

    expect(pillLabels()).toEqual(FULL_YEAR_THEN(APR_TO_MAR));

    await userEvent.click(screen.getByRole("button", { name: "Full year" }));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/budget-grid?year=2026&period=financial", expect.anything()),
    );
    const [headerRow] = await screen.findAllByRole("row");
    const headers = within(headerRow).getAllByRole("columnheader").map((header) => header.textContent);
    expect(headers).toEqual(["Category", ...APR_TO_MAR]);
  });

  it.each([
    [4, "2026-2027 Financial Year", "2025-2026 Financial Year"],
    [10, "2025-2026 Financial Year", "2024-2025 Financial Year"],
  ])(
    "stops the Next arrow at the year containing today for a start month of %i",
    async (startMonth, currentLabel, previousLabel) => {
      respondWithStartMonth(startMonth, { earliest: "2024-01-01" });
      render(<App />);
      await screen.findByText(currentLabel);
      expect(screen.getByRole("button", { name: "Next year" })).toBeDisabled();

      await userEvent.click(screen.getByRole("button", { name: "Previous year" }));
      await screen.findByText(previousLabel);
      expect(screen.getByRole("button", { name: "Next year" })).toBeEnabled();

      await userEvent.click(screen.getByRole("button", { name: "Next year" }));
      await screen.findByText(currentLabel);
      expect(screen.getByRole("button", { name: "Next year" })).toBeDisabled();
    },
  );

  it("starts Transactions at the saved start month: its request, month filter and Export default range", async () => {
    respondWithStartMonth(4);
    render(<App />);
    await screen.findByText("$8,000");

    await userEvent.click(screen.getByRole("button", { name: "Transactions" }));
    await screen.findByText("Woolworths");

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/transactions?year=2026&month=4", expect.anything()),
    );
    const options = within(screen.getByLabelText("Month"))
      .getAllByRole("option")
      .map((option) => option.textContent);
    expect(options).toEqual(["All months", ...APR_TO_MAR]);

    await userEvent.click(screen.getByRole("button", { name: "More options" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Export transactions" }));
    expect(screen.getByLabelText("Start date")).toHaveValue("2026-04-01");
    expect(screen.getByLabelText("End date")).toHaveValue("2027-03-31");
  });

  it("bounds the Previous arrow at the year containing the earliest Transaction, by the saved start month", async () => {
    // May 2026 starts the April-start 2026 year, but sits inside the July-start 2025 year.
    respondWithStartMonth(4, { earliest: "2026-05-10" });
    render(<App />);
    await screen.findByText("2026-2027 Financial Year");

    expect(screen.getByRole("button", { name: "Previous year" })).toBeDisabled();
  });

  it("labels a January start with a single year and hides the Financial Year/Calendar Year switcher", async () => {
    respondWithStartMonth(1);
    render(<App />);

    expect(await screen.findByText("2026 Financial Year")).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Select year" })).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Financial Year or Calendar Year" })).not.toBeInTheDocument();
    expect(pillLabels()).toEqual(FULL_YEAR_THEN(JAN_TO_DEC));
  });

  it("steps through January-start Financial Years with the arrows, labelled with a single year", async () => {
    respondWithStartMonth(1);
    render(<App />);
    await screen.findByText("2026 Financial Year");

    await userEvent.click(screen.getByRole("button", { name: "Previous year" }));

    expect(await screen.findByText("2025 Financial Year")).toBeInTheDocument();
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/annual-overview?year=2025&period=financial", expect.anything()),
    );
  });

  it("ignores a Calendar Year framing stored in the browser while the start is January", async () => {
    localStorage.setItem("dashboard.periodType", "calendar");
    respondWithStartMonth(1);
    render(<App />);

    expect(await screen.findByText("2026 Financial Year")).toBeInTheDocument();
    expect(screen.queryByText("Calendar Year 2026")).not.toBeInTheDocument();
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/annual-overview?year=2026&period=financial", expect.anything()),
    );
    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining("period=calendar"), expect.anything());
  });

  it("still offers Calendar Year with a start other than January", async () => {
    respondWithStartMonth(4);
    render(<App />);
    await screen.findByText("2026-2027 Financial Year");

    await userEvent.click(screen.getByRole("button", { name: "Calendar Year" }));

    expect(await screen.findByText("Calendar Year 2026")).toBeInTheDocument();
    expect(pillLabels()).toEqual(FULL_YEAR_THEN(JAN_TO_DEC));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/annual-overview?year=2026&period=calendar", expect.anything()),
    );
  });

  it("brings the switcher back after the start moves off January, restoring the stored Calendar Year framing", async () => {
    localStorage.setItem("dashboard.periodType", "calendar");
    respondWithStartMonth(1);
    render(<App />);
    await screen.findByText("2026 Financial Year");

    await chooseStartMonth("April");
    await userEvent.click(screen.getByRole("button", { name: "Overview" }));

    expect(await screen.findByText("Calendar Year 2026")).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Financial Year or Calendar Year" })).toBeInTheDocument();
  });

  async function chooseStartMonth(monthName) {
    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    await userEvent.selectOptions(await screen.findByRole("combobox", { name: "Financial Year start month" }), monthName);
    await userEvent.click(screen.getByRole("button", { name: "Save settings" }));
  }

  it("offers January to December in Settings, showing the saved start month", async () => {
    respondWithStartMonth(4);
    render(<App />);
    await screen.findByText("$8,000");

    await userEvent.click(screen.getByRole("button", { name: "Settings" }));

    const dropdown = await screen.findByRole("combobox", { name: "Financial Year start month" });
    expect(dropdown).toHaveValue("4");
    expect(within(dropdown).getAllByRole("option").map((option) => option.textContent)).toEqual([
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ]);
  });

  it("saves the chosen start month to the settings endpoint", async () => {
    respondWithStartMonth(7);
    render(<App />);
    await screen.findByText("$8,000");

    await chooseStartMonth("April");

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/settings",
        expect.objectContaining({ method: "PUT", body: JSON.stringify({ financial_year_start_month: 4 }) }),
      ),
    );
  });

  it("regroups the Dashboard as soon as a new start month is saved, landing on the year containing today", async () => {
    respondWithStartMonth(7);
    render(<App />);
    await screen.findByText("2026-2027 Financial Year");

    await chooseStartMonth("October");
    await userEvent.click(screen.getByRole("button", { name: "Overview" }));

    expect(await screen.findByText("2025-2026 Financial Year")).toBeInTheDocument();
    expect(pillLabels()).toEqual(FULL_YEAR_THEN(["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]));
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/annual-overview?year=2025&period=financial", expect.anything()),
    );
  });

  it("shows the server's message when a start month is refused", async () => {
    respondWithStartMonth(7);
    const answer = fetchMock.getMockImplementation();
    fetchMock.mockImplementation(async (url, options = {}) =>
      url.startsWith("/api/settings") && options.method === "PUT"
        ? { ok: false, status: 400, json: async () => ({ error: "financial_year_start_month must be a month number from 1 to 12, got 13" }) }
        : answer(url, options),
    );
    render(<App />);
    await screen.findByText("$8,000");

    await chooseStartMonth("April");

    expect(await screen.findByRole("alert")).toHaveTextContent("month number from 1 to 12");
  });
});

describe("Version", () => {
  const VERSION = { version: "0.4.1", history: null };

  // Every endpoint the tabs touch, plus the Version endpoint. `version` is the
  // whole response, or null for a backend that fails the request.
  function respondWithVersion(version = VERSION) {
    const bodies = {
      "/api/annual-overview": annualWithSpending(),
      "/api/overview": monthWithSpending(2026, 8),
      "/api/latest-transaction-date": { date: "2026-08-03" },
      "/api/transaction-date-range": { earliest: "2025-12-17", latest: "2026-08-03" },
      "/api/transactions": [],
      "/api/budget-editor": { Income: [], Expense: [], Debt: [] },
      "/api/budget-grid": { Income: [], Expense: [], Debt: [] },
      "/api/budget-suggestion": { write_up: null, generated_at: null },
      "/api/recurring-rules": [],
      "/api/categories": [],
    };
    fetchMock.mockImplementation(async (url) => {
      if (url.startsWith("/api/version")) {
        return version === null
          ? { ok: false, status: 500, json: async () => ({ error: "boom" }) }
          : { ok: true, status: 200, json: async () => version };
      }
      const match = Object.keys(bodies).find((path) => url.startsWith(path));
      return { ok: true, status: 200, json: async () => bodies[match] };
    });
  }

  it("shows the Version as v<version> directly under the Dashboard title", async () => {
    respondWithVersion();
    render(<App />);

    const version = await screen.findByText("v0.4.1");
    const title = screen.getByRole("heading", { name: "Budgeting Dashboard" });

    expect(title.nextElementSibling).toBe(version);
  });

  it("keeps the Version under the title on every tab", async () => {
    respondWithVersion();
    render(<App />);
    await screen.findByText("v0.4.1");

    for (const tab of ["Transactions", "Budget", "Settings", "Overview"]) {
      await userEvent.click(screen.getByRole("button", { name: tab }));
      expect(screen.getByText("v0.4.1")).toBeInTheDocument();
    }
  });

  it("still renders the Dashboard, without a Version line, when the Version can't be read", async () => {
    respondWithVersion(null);
    render(<App />);

    expect(await screen.findByText("$8,000")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Budgeting Dashboard" })).toBeInTheDocument();
    expect(screen.queryByText(/^v\d/)).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("Version History", () => {
  const HISTORY = [
    { version: "0.4.1", date: "2026-10-11", entries: ["Updating no longer stops on leftover files."] },
    { version: "0.4.0", date: "2026-10-04", entries: ["Added a thing.", "Fixed another thing."] },
  ];

  // Every endpoint the tabs touch, with the Version, its history and the saved
  // settings chosen per test. `history` null is a changelog that can't be read.
  function respondWith({ version = "0.4.1", history = HISTORY, settings = {} } = {}) {
    const bodies = {
      "/api/annual-overview": annualWithSpending(),
      "/api/overview": monthWithSpending(2026, 8),
      "/api/latest-transaction-date": { date: "2026-08-03" },
      "/api/transaction-date-range": { earliest: "2025-12-17", latest: "2026-08-03" },
      "/api/transactions": [],
      "/api/budget-editor": { Income: [], Expense: [], Debt: [] },
      "/api/budget-grid": { Income: [], Expense: [], Debt: [] },
      "/api/budget-suggestion": { write_up: null, generated_at: null },
      "/api/recurring-rules": [],
      "/api/categories": [],
      "/api/settings": { currency: "AUD", financial_year_start_month: 7, date_order: "day-first", ...settings },
      "/api/version": { version, history },
    };
    fetchMock.mockImplementation(async (url) => {
      const match = Object.keys(bodies).find((path) => url.startsWith(path));
      return { ok: true, status: 200, json: async () => bodies[match] };
    });
  }

  async function openHistory() {
    await userEvent.click(await screen.findByRole("button", { name: "Version history" }));
  }

  it("puts a Version history link in the header on every tab, including Settings", async () => {
    respondWith();
    render(<App />);

    for (const tab of ["Overview", "Transactions", "Budget", "Settings"]) {
      await userEvent.click(await screen.findByRole("button", { name: tab }));
      expect(within(screen.getByRole("banner")).getByRole("button", { name: "Version history" })).toBeInTheDocument();
    }
  });

  it("keeps the link, above the period switcher, when the switcher is shown", async () => {
    respondWith();
    render(<App />);

    const link = await screen.findByRole("button", { name: "Version history" });
    const switcher = screen.getByRole("group", { name: "Select year" });

    expect(link.compareDocumentPosition(switcher) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("keeps the link when the period switcher is hidden by a January Financial Year start", async () => {
    respondWith({ settings: { financial_year_start_month: 1 } });
    render(<App />);

    expect(await screen.findByRole("button", { name: "Version history" })).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Financial Year or Calendar Year" })).not.toBeInTheDocument();
  });

  it("lists the Versions newest-first, with dates in the Date Order, marking the running Version Current", async () => {
    respondWith({ settings: { date_order: "month-first" } });
    render(<App />);
    await openHistory();

    const versions = await screen.findAllByRole("listitem", { name: /^v\d/ });

    expect(versions.map((item) => item.getAttribute("aria-label"))).toEqual(["v0.4.1", "v0.4.0"]);
    expect(within(versions[0]).getByText("Oct 11, 2026")).toBeInTheDocument();
    expect(within(versions[0]).getByText("Current")).toBeInTheDocument();
    expect(within(versions[0]).getByText("Updating no longer stops on leftover files.")).toBeInTheDocument();
    expect(within(versions[1]).getByText("Oct 4, 2026")).toBeInTheDocument();
    expect(within(versions[1]).queryByText("Current")).not.toBeInTheDocument();
    expect(within(versions[1]).getByText("Fixed another thing.")).toBeInTheDocument();
  });

  it("writes the dates day-first by default", async () => {
    respondWith();
    render(<App />);
    await openHistory();

    expect(await screen.findByText("11 Oct 2026")).toBeInTheDocument();
  });

  it("returns to the same tab, year and month selection from Back to Dashboard", async () => {
    respondWith();
    render(<App />);
    // Step back a year, then pick a month that is neither the default (Full
    // year) nor the month of the latest Transaction (Aug), so a reset to either
    // would be noticed.
    await userEvent.click(await screen.findByRole("button", { name: "Previous year" }));
    await screen.findByText("2025-2026 Financial Year");
    await userEvent.click(screen.getByRole("button", { name: "Dec" }));
    await openHistory();
    await userEvent.click(await screen.findByRole("button", { name: "Back to Dashboard" }));

    expect(screen.getByText("2025-2026 Financial Year")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dec" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Overview" })).toHaveAttribute("aria-current", "page");
    expect(screen.queryByText("Current")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Transactions" }));
    await openHistory();
    await userEvent.click(await screen.findByRole("button", { name: "Back to Dashboard" }));

    expect(screen.getByRole("button", { name: "Transactions" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("2025-2026 Financial Year")).toBeInTheDocument();

    // The Overview month survives a trip through another tab and the history.
    await userEvent.click(screen.getByRole("button", { name: "Overview" }));

    expect(screen.getByRole("button", { name: "Dec" })).toHaveAttribute("aria-pressed", "true");
  });

  it("says the history isn't available, and still shows the Version, when there is none", async () => {
    respondWith({ history: null });
    render(<App />);
    await openHistory();

    expect(await screen.findByText("Version history isn't available")).toBeInTheDocument();
    expect(screen.getByText("v0.4.1")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("lists the Versions with no Current marker when the running Version has no entry", async () => {
    respondWith({ version: "0.9.9" });
    render(<App />);
    await openHistory();

    expect(await screen.findAllByRole("listitem", { name: /^v\d/ })).toHaveLength(2);
    expect(screen.queryByText("Current")).not.toBeInTheDocument();
  });
});
