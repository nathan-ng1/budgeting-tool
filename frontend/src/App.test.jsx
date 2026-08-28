import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App.jsx";

const ZERO_STAT_TILES = { income: 0, expenses: 0, debt: 0, net_balance: 0, transferred: 0 };
const ZERO_ALLOCATION = {
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
    top_expenses: [],
    expenses_over_time: { daily: [], total: 0, daily_average: 0 },
    ...overrides,
  };
}

function monthWithSpending(year, month, overrides = {}) {
  return monthOverview({
    year,
    month,
    stat_tiles: { income: 5240, expenses: 3667, debt: 0, net_balance: 1573, transferred: 900 },
    income_allocation: {
      expenses_amount: 3667,
      expenses_pct: 70,
      debt_amount: 0,
      debt_pct: 0,
      transferred_amount: 900,
      transferred_pct: 17.2,
      remaining_amount: 673,
      remaining_pct: 12.8,
      over_income_amount: 0,
      over_income_pct: 0,
    },
    spending_by_category: [{ category: "Groceries", amount: 3667, pct_of_expenses: 100 }],
    budgeted_vs_actual: [{ type: "Expense", category: "Groceries", budgeted: 650, actual: 3667, diff: -3017, pct: 564.2 }],
    top_expenses: [{ notes: "Woolworths", category: "Groceries", date: `${year}-0${month}-05`, amount: 3667 }],
    expenses_over_time: {
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
  return { year: month >= 7 ? 2026 : 2027, month, ...ZERO_STAT_TILES };
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
    top_expenses: [],
    month_by_month: ZERO_MONTHS,
    income_vs_expenses_by_month: ZERO_MONTHS,
    ...overrides,
  };
}

function annualWithSpending(overrides = {}) {
  const months = ZERO_MONTHS.map((m, index) =>
    index === 0 ? { ...m, income: 5240, expenses: 3810, debt: 0, net_balance: 1430, transferred: 900 } : m,
  );

  return annualOverview({
    stat_tiles: { income: 8000, expenses: 6000, debt: 0, net_balance: 2000, transferred: 1000 },
    monthly_average: { income: 4000, expenses: 3000, debt: 0, net_balance: 1000, transferred: 500 },
    income_allocation: {
      expenses_amount: 6000,
      expenses_pct: 75,
      debt_amount: 0,
      debt_pct: 0,
      transferred_amount: 1000,
      transferred_pct: 12.5,
      remaining_amount: 1000,
      remaining_pct: 12.5,
      over_income_amount: 0,
      over_income_pct: 0,
    },
    spending_by_category: [{ category: "Groceries", amount: 6000, pct_of_expenses: 100 }],
    // Full year's Budgeted is a real per-Category rollup across elapsed months (ADR-0013).
    budgeted_vs_actual: [{ type: "Expense", category: "Groceries", budgeted: 3000, actual: 6000, diff: -3000, pct: 200.0 }],
    top_expenses: [{ notes: "Woolworths", category: "Groceries", date: "2026-07-05", amount: 6000 }],
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
    expect(screen.getByText("$1,000 / month · excludes transfers")).toBeInTheDocument(); // Net Balance average
    expect(screen.getByRole("heading", { name: "Where did my income go?" })).toBeInTheDocument();
  });

  it("renders Full year's Spending by Category, Budgeted vs Actual, Month by month, Income, Expenses & Debt by Month, and Top 10 expenses", async () => {
    respondWith();
    render(<App />);
    await screen.findByText("$8,000");

    expect(screen.getByRole("heading", { name: "Spending by Category" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Budgeted vs Actual" })).toBeInTheDocument();
    // Full year's Budgeted vs Actual now reports a real per-Category rollup,
    // not ADR-0011's placeholder "—" (ADR-0013).
    expect(screen.getByRole("row", { name: /Groceries/ })).toHaveTextContent("$3,000");

    expect(screen.getByRole("heading", { name: "Month by month" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Income, Expenses & Debt by Month" })).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Top 10 expenses" })).toBeInTheDocument();
    expect(screen.getByText("Woolworths")).toBeInTheDocument();

    // Per-month-only sections stay off Full year.
    expect(screen.queryByRole("heading", { name: "Expenses over time" })).not.toBeInTheDocument();
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
    expect(screen.getByRole("heading", { name: "Top 5 expenses" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Expenses over time" })).toBeInTheDocument();
    expect(screen.getByText("Woolworths")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aug" })).toHaveAttribute("aria-pressed", "true");
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

    await userEvent.click(screen.getByRole("button", { name: "Aug" }));
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

    await userEvent.click(screen.getByRole("button", { name: "Aug" }));
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
    expect(screen.getByRole("heading", { name: "Expenses over time" })).toBeInTheDocument();

    // ...with zeroes and plain empty copy rather than a crash or blank panels.
    expect(screen.getAllByText("$0").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/No expenses recorded/i)).toHaveLength(2);
    expect(screen.getByText(/No spending or Category Budgets/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Debt" })).toBeInTheDocument();
    expect(screen.getByText(/No Debt repayments recorded/i)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("renders the Debt card between Spending by Category/Budgeted vs Actual and Top 5/Expenses over time, for a month with Debt", async () => {
    respondWith({
      month: monthWithSpending(2026, 8, {
        stat_tiles: { income: 5240, expenses: 3667, debt: 875, net_balance: 698, transferred: 900 },
        debt_summary: [{ notes: "Werribee", amount: 875, pct_of_debt: 100 }],
      }),
    });
    render(<App />);
    await screen.findByText("$8,000");

    await userEvent.click(screen.getByRole("button", { name: "Aug" }));
    await screen.findByText("$5,240");

    const headings = screen.getAllByRole("heading").map((h) => h.textContent);
    expect(headings.indexOf("Budgeted vs Actual")).toBeLessThan(headings.indexOf("Debt"));
    expect(headings.indexOf("Debt")).toBeLessThan(headings.indexOf("Top 5 expenses"));
    expect(screen.getByText("Werribee")).toBeInTheDocument();
    expect(screen.getAllByText("$875").length).toBeGreaterThan(0);
    expect(screen.queryByText(/month average/)).not.toBeInTheDocument();
  });

  it("groups Spending by Category, Budgeted vs Actual, and Debt into the wide-pair layout, for a month", async () => {
    respondWith({
      month: monthWithSpending(2026, 8, {
        stat_tiles: { income: 5240, expenses: 3667, debt: 875, net_balance: 698, transferred: 900 },
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
        stat_tiles: { income: 8000, expenses: 6000, debt: 1600, net_balance: 400, transferred: 1000 },
        monthly_average: { income: 4000, expenses: 3000, debt: 800, net_balance: 200, transferred: 500 },
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

  it("groups Month by month, Budgeted vs Actual, and Debt into the wide-pair layout, and pairs Spending by Category with Top expenses, for Full year", async () => {
    respondWith({
      annual: annualWithSpending({
        stat_tiles: { income: 8000, expenses: 6000, debt: 1600, net_balance: 400, transferred: 1000 },
        monthly_average: { income: 4000, expenses: 3000, debt: 800, net_balance: 200, transferred: 500 },
        debt_summary: [{ notes: "Werribee", amount: 1600, pct_of_debt: 100 }],
      }),
    });
    render(<App />);
    await screen.findByText("$8,000");

    const widePair = screen.getByRole("heading", { name: "Budgeted vs Actual" }).closest(".row--wide-pair");
    expect(widePair).not.toBeNull();
    expect(within(widePair).getByRole("heading", { name: "Month by month" })).toBeInTheDocument();
    expect(within(widePair).getByRole("heading", { name: "Debt" })).toBeInTheDocument();
    expect(within(widePair).queryByRole("heading", { name: "Spending by Category" })).not.toBeInTheDocument();

    const split = screen.getByRole("heading", { name: "Spending by Category" }).closest(".row--split");
    expect(split).not.toBeNull();
    expect(within(split).getByRole("heading", { name: "Top 10 expenses" })).toBeInTheDocument();
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

    const nav = screen.getByRole("navigation");

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
      expect(screen.queryByRole("heading", { name: "Expenses over time" })).not.toBeInTheDocument();
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
});
