import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Transactions from "./Transactions.jsx";

function transaction(overrides = {}) {
  return {
    id: 1,
    date: "2026-08-05",
    amount: 42.5,
    type: "Expense",
    category: "Groceries",
    notes: "Woolworths",
    ...overrides,
  };
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

function respondWith(body) {
  fetchMock.mockResolvedValue({ ok: true, status: 200, json: async () => body });
}

describe("Transactions", () => {
  it("renders the list in the order the backend returns it (newest-first)", async () => {
    // The backend sorts newest-first (see ADR-0010/queries.get_financial_year_transactions);
    // the component just renders what it's given, so the mock returns it that way here.
    respondWith([
      transaction({ id: 2, date: "2027-02-01", notes: "Employer", amount: 4000, type: "Income", category: "Salary" }),
      transaction({ id: 1, date: "2026-08-01", notes: "Woolworths" }),
    ]);
    render(<Transactions />);

    expect(fetchMock).toHaveBeenCalledWith("/api/transactions?year=2026&month=7", expect.anything());

    const rows = await screen.findAllByRole("row");
    expect(rows[1]).toHaveTextContent("Employer");
    expect(rows[2]).toHaveTextContent("Woolworths");
  });

  it("renders the Date, Amount, Type, Category, Notes columns in that order", async () => {
    respondWith([transaction()]);
    render(<Transactions />);

    const headers = (await screen.findAllByRole("columnheader")).map((header) => header.textContent);
    expect(headers).toEqual(["Date", "Amount", "Type", "Category", "Notes"]);
  });

  it("renders Amount plain, with no colour or sign", async () => {
    respondWith([transaction({ amount: 42.5 })]);
    render(<Transactions />);

    expect(await screen.findByText("$42.50")).toBeInTheDocument();
  });

  it("says so plainly when the current Financial Year has no Transactions", async () => {
    respondWith([]);
    render(<Transactions />);

    expect(await screen.findByText(/No Transactions yet/i)).toBeInTheDocument();
  });

  it("surfaces a failure to load rather than showing an empty list", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });
    render(<Transactions />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/500/);
  });
});
