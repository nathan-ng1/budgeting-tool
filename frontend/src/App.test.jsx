import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App.jsx";

function overview({ year = 2026, month = 8, ...overrides } = {}) {
  return {
    year,
    month,
    stat_tiles: { income: 0, expenses: 0, net_balance: 0, transferred: 0 },
    income_allocation: {
      expenses_amount: 0,
      expenses_pct: 0,
      transferred_amount: 0,
      transferred_pct: 0,
      remaining_amount: 0,
      remaining_pct: 0,
      over_income_amount: 0,
      over_income_pct: 0,
    },
    spending_by_category: [],
    budgeted_vs_actual: [],
    top_expenses: [],
    expenses_over_time: { daily: [], total: 0, daily_average: 0 },
    ...overrides,
  };
}

function withSpending(year, month) {
  return overview({
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

function respondWith(body, latestTransactionDate = "2026-08-03") {
  fetchMock.mockImplementation(async (url) => ({
    ok: true,
    status: 200,
    json: async () => (url.startsWith("/api/latest-transaction-date") ? { date: latestTransactionDate } : body),
  }));
}

describe("App", () => {
  it("opens on the current calendar month within its Financial Year", async () => {
    respondWith(withSpending(2026, 8));
    render(<App />);

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/overview?year=2026&month=8", expect.anything()));

    expect(screen.getByText("2026-2027 Financial Year")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aug" })).toHaveAttribute("aria-pressed", "true");
  });

  it("renders every section from the endpoint's response", async () => {
    respondWith(withSpending(2026, 8));
    render(<App />);

    expect(await screen.findByText("$5,240")).toBeInTheDocument(); // Real Income tile
    expect(screen.getByRole("heading", { name: "Where did my income go?" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Spending by Category" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Budgeted vs Actual" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Top 5 expenses" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Expenses over time" })).toBeInTheDocument();
    expect(screen.getByText("Woolworths")).toBeInTheDocument();
  });

  it("re-fetches and re-renders every section when the month changes", async () => {
    fetchMock.mockImplementation(async (url) => ({
      ok: true,
      status: 200,
      json: async () => (url.includes("month=9") ? overview({ year: 2026, month: 9 }) : withSpending(2026, 8)),
    }));
    render(<App />);

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
        return { ok: true, status: 200, json: async () => overview({ year: 2026, month: 9 }) };
      }
      return { ok: true, status: 200, json: async () => withSpending(2026, 8) };
    });
    render(<App />);

    expect(await screen.findByText("$5,240")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Sep" }));

    await waitFor(() => expect(screen.queryByText("$5,240")).not.toBeInTheDocument());
    releaseSeptember();
    await waitFor(() => expect(screen.getByRole("heading", { name: "Spending by Category" })).toBeInTheDocument());
  });

  it("renders a month with no Transactions as a coherent empty state, not an error", async () => {
    respondWith(overview({ year: 2026, month: 9 }));
    render(<App />);

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
    routeTo({ "/api/overview": withSpending(2026, 8), "/api/recurring-rules": [], "/api/categories": {} });
    render(<App />);
    expect(await screen.findByText("$5,240")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Settings" }));

    expect(await screen.findByRole("heading", { name: "Recurring Transactions Config" })).toBeInTheDocument();
    expect(screen.getByText("Settings")).toHaveAttribute("aria-current", "page");
  });

  it("puts the Overview's month selector away while Settings is open", async () => {
    routeTo({ "/api/overview": withSpending(2026, 8), "/api/recurring-rules": [], "/api/categories": {} });
    render(<App />);
    expect(await screen.findByText("$5,240")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Settings" }));

    // The month selector picks a month for the Overview - it means nothing here.
    await waitFor(() => expect(screen.queryByRole("group", { name: "Select month" })).not.toBeInTheDocument());
    expect(screen.queryByText("$5,240")).not.toBeInTheDocument();
  });

  it("comes back to the Overview with its month still selected", async () => {
    routeTo({ "/api/overview": withSpending(2026, 8), "/api/recurring-rules": [], "/api/categories": {} });
    render(<App />);
    expect(await screen.findByText("$5,240")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Settings" }));
    await screen.findByRole("heading", { name: "Recurring Transactions Config" });
    await userEvent.click(screen.getByRole("button", { name: "Overview" }));

    expect(await screen.findByText("$5,240")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aug" })).toHaveAttribute("aria-pressed", "true");
  });

  it("leaves Transactions and Budget unwired, since they have no screens yet", async () => {
    respondWith(withSpending(2026, 8));
    render(<App />);
    await screen.findByText("$5,240");

    expect(screen.queryByRole("button", { name: "Transactions" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Budget" })).not.toBeInTheDocument();
  });

  it("dates the page by the newest Transaction in the log, not by today", async () => {
    // The clock says 21 August; the Transaction Log only runs to the 3rd.
    respondWith(withSpending(2026, 8), "2026-08-03");
    render(<App />);

    expect(await screen.findByText("As at 3 August")).toBeInTheDocument();
    expect(screen.queryByText("As at 21 August")).not.toBeInTheDocument();
  });

  it("keeps the As at date still when the reader switches months", async () => {
    fetchMock.mockImplementation(async (url) => ({
      ok: true,
      status: 200,
      json: async () =>
        url.startsWith("/api/latest-transaction-date")
          ? { date: "2026-08-03" }
          : url.includes("month=9")
            ? overview({ year: 2026, month: 9 })
            : withSpending(2026, 8),
    }));
    render(<App />);
    expect(await screen.findByText("As at 3 August")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Sep" }));

    await waitFor(() => expect(screen.getByRole("button", { name: "Sep" })).toHaveAttribute("aria-pressed", "true"));
    expect(screen.getByText("As at 3 August")).toBeInTheDocument();
  });

  it("says nothing about a date when the Transaction Log is empty", async () => {
    respondWith(overview({ year: 2026, month: 8 }), null);
    render(<App />);

    await screen.findByRole("heading", { name: "Spending by Category" });
    expect(screen.queryByText(/^As at/)).not.toBeInTheDocument();
  });

  it("shows the nav tabs, with only Overview marked current", async () => {
    respondWith(withSpending(2026, 8));
    render(<App />);

    const nav = screen.getByRole("navigation");

    expect(within(nav).getByText("Transactions")).toBeInTheDocument();
    expect(within(nav).getByText("Budget")).toBeInTheDocument();
    expect(within(nav).getByText("Settings")).toBeInTheDocument();
    expect(within(nav).getByText("Overview")).toHaveAttribute("aria-current", "page");
  });
});
