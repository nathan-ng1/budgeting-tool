import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App.jsx";

const ZERO_STAT_TILES = { income: 0, expenses: 0, net_balance: 0, transferred: 0 };
const ZERO_ALLOCATION = {
  expenses_amount: 0,
  expenses_pct: 0,
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
    top_expenses: [],
    expenses_over_time: { daily: [], total: 0, daily_average: 0 },
    ...overrides,
  };
}

function monthWithSpending(year, month) {
  return monthOverview({
    year,
    month,
    stat_tiles: { income: 5240, expenses: 3667, net_balance: 1573, transferred: 900 },
    income_allocation: {
      expenses_amount: 3667,
      expenses_pct: 70,
      transferred_amount: 900,
      transferred_pct: 17.2,
      remaining_amount: 673,
      remaining_pct: 12.8,
      over_income_amount: 0,
      over_income_pct: 0,
    },
    spending_by_category: [{ category: "Groceries", amount: 3667, pct_of_expenses: 100 }],
    budgeted_vs_actual: [{ category: "Groceries", expected: 650, actual: 3667, diff: -3017, pct: 564.2 }],
    top_expenses: [{ notes: "Woolworths", category: "Groceries", date: `${year}-0${month}-05`, amount: 3667 }],
    expenses_over_time: {
      daily: [
        { date: `${year}-0${month}-01`, cumulative: 0 },
        { date: `${year}-0${month}-05`, cumulative: 3667 },
      ],
      total: 3667,
      daily_average: 118,
    },
  });
}

function annualOverview(overrides = {}) {
  return {
    year: 2026,
    elapsed_months: 2,
    stat_tiles: ZERO_STAT_TILES,
    monthly_average: ZERO_STAT_TILES,
    income_allocation: ZERO_ALLOCATION,
    spending_by_category: [],
    budgeted_vs_actual: [],
    top_expenses: [],
    ...overrides,
  };
}

function annualWithSpending() {
  return annualOverview({
    stat_tiles: { income: 8000, expenses: 6000, net_balance: 2000, transferred: 1000 },
    monthly_average: { income: 4000, expenses: 3000, net_balance: 1000, transferred: 500 },
    income_allocation: {
      expenses_amount: 6000,
      expenses_pct: 75,
      transferred_amount: 1000,
      transferred_pct: 12.5,
      remaining_amount: 1000,
      remaining_pct: 12.5,
      over_income_amount: 0,
      over_income_pct: 0,
    },
    spending_by_category: [{ category: "Groceries", amount: 6000, pct_of_expenses: 100 }],
    // expected is always null for Full year, regardless of any Category Budget (ADR-0011).
    budgeted_vs_actual: [{ category: "Groceries", expected: null, actual: 6000, diff: null, pct: null }],
    top_expenses: [{ notes: "Woolworths", category: "Groceries", date: "2026-07-05", amount: 6000 }],
  });
}

let fetchMock;

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date(2026, 7, 21)); // 21 August 2026 - Financial Year 2026
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function routeTo(bodies) {
  fetchMock.mockImplementation(async (url) => {
    const match = Object.keys(bodies).find((path) => url.startsWith(path));
    return { ok: true, status: 200, json: async () => bodies[match] };
  });
}

// Routes every endpoint an Overview-tab load touches, with sensible defaults -
// most tests only care about overriding one of them.
function respondWith({
  annual = annualWithSpending(),
  month = monthWithSpending(2026, 8),
  latestTransactionDate = "2026-08-03",
} = {}) {
  routeTo({
    "/api/annual-overview": annual,
    "/api/overview": month,
    "/api/latest-transaction-date": { date: latestTransactionDate },
  });
}

describe("App", () => {
  it("opens on Full year by default, for the Financial Year containing today", async () => {
    respondWith();
    render(<App />);

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/annual-overview?year=2026", expect.anything()),
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

  it("renders Full year's Spending by Category, Budgeted vs Actual, and Top 10 expenses, but not the still-deferred sections", async () => {
    respondWith();
    render(<App />);
    await screen.findByText("$8,000");

    expect(screen.getByRole("heading", { name: "Spending by Category" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Budgeted vs Actual" })).toBeInTheDocument();
    // Every Budgeted vs Actual row reads "—" for Expected/Diff/% (ADR-0011).
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);

    expect(screen.getByRole("heading", { name: "Top 10 expenses" })).toBeInTheDocument();
    expect(screen.getByText("Woolworths")).toBeInTheDocument();

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
      json: async () =>
        url.includes("month=9") ? monthOverview({ year: 2026, month: 9 }) : monthWithSpending(2026, 8),
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
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("surfaces a backend failure instead of rendering a half-empty page", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/500/);
  });

  it("opens the Recurring Transactions Config screen from the Settings tab", async () => {
    routeTo({ "/api/annual-overview": annualWithSpending(), "/api/recurring-rules": [], "/api/categories": {} });
    render(<App />);
    expect(await screen.findByText("$8,000")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Settings" }));

    expect(await screen.findByRole("heading", { name: "Recurring Transactions Config" })).toBeInTheDocument();
    expect(screen.getByText("Settings")).toHaveAttribute("aria-current", "page");
  });

  it("puts the Overview's month selector away while Settings is open", async () => {
    routeTo({ "/api/annual-overview": annualWithSpending(), "/api/recurring-rules": [], "/api/categories": {} });
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
      "/api/categories": {},
    });
    render(<App />);
    expect(await screen.findByText("$8,000")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Aug" }));
    expect(await screen.findByText("$5,240")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    await screen.findByRole("heading", { name: "Recurring Transactions Config" });
    await userEvent.click(screen.getByRole("button", { name: "Overview" }));

    expect(await screen.findByText("$5,240")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aug" })).toHaveAttribute("aria-pressed", "true");
  });

  it("leaves Budget unwired, since it has no screen yet", async () => {
    respondWith();
    render(<App />);
    await screen.findByText("$8,000");

    expect(screen.queryByRole("button", { name: "Budget" })).not.toBeInTheDocument();
  });

  it("opens the Transactions tab and lists that Financial Year's Transactions newest-first", async () => {
    routeTo({
      "/api/annual-overview": annualWithSpending(),
      "/api/transactions": [
        { id: 1, date: "2026-08-01", amount: 42.5, type: "Expense", category: "Groceries", notes: "Woolworths" },
        { id: 2, date: "2027-02-01", amount: 4000, type: "Income", category: "Salary", notes: "Employer" },
      ],
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
});
