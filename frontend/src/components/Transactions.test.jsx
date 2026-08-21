import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

function rowTexts() {
  return screen.getAllByRole("row").slice(1).map((row) => row.textContent);
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

  describe("filtering, searching, and sorting", () => {
    const groceries = transaction({ id: 1, date: "2026-08-05", amount: 42.5, type: "Expense", category: "Groceries", notes: "Woolworths" });
    const fuel = transaction({ id: 2, date: "2026-09-10", amount: 60, type: "Expense", category: "Transport", notes: "Fuel stop" });
    const salary = transaction({ id: 3, date: "2026-08-20", amount: 4000, type: "Income", category: "Salary", notes: "Employer Pty Ltd" });

    beforeEach(() => {
      respondWith([groceries, fuel, salary]);
    });

    it("filters by Category", async () => {
      render(<Transactions />);
      await screen.findAllByRole("row");

      await userEvent.selectOptions(screen.getByLabelText(/category/i), "Groceries");

      expect(rowTexts()).toHaveLength(1);
      expect(rowTexts()[0]).toContain("Woolworths");
    });

    it("filters by Month, offering only months in the current Financial Year", async () => {
      render(<Transactions />);
      await screen.findAllByRole("row");

      const monthSelect = screen.getByLabelText(/month/i);
      const optionLabels = within(monthSelect).getAllByRole("option").map((option) => option.textContent);
      expect(optionLabels).toContain("Jul");
      expect(optionLabels).toHaveLength(13); // "All months" + 12

      await userEvent.selectOptions(monthSelect, "Sep");

      expect(rowTexts()).toHaveLength(1);
      expect(rowTexts()[0]).toContain("Fuel stop");
    });

    it("filters by Type", async () => {
      render(<Transactions />);
      await screen.findAllByRole("row");

      await userEvent.selectOptions(screen.getByLabelText(/type/i), "Income");

      expect(rowTexts()).toHaveLength(1);
      expect(rowTexts()[0]).toContain("Employer Pty Ltd");
    });

    it("combines Category, Month, and Type filters", async () => {
      render(<Transactions />);
      await screen.findAllByRole("row");

      await userEvent.selectOptions(screen.getByLabelText(/type/i), "Expense");
      await userEvent.selectOptions(screen.getByLabelText(/category/i), "Transport");

      expect(rowTexts()).toHaveLength(1);
      expect(rowTexts()[0]).toContain("Fuel stop");
    });

    it("searches Notes case-insensitively, combined with active filters", async () => {
      render(<Transactions />);
      await screen.findAllByRole("row");

      await userEvent.type(screen.getByLabelText(/search/i), "EMPLOYER");

      expect(rowTexts()).toHaveLength(1);
      expect(rowTexts()[0]).toContain("Employer Pty Ltd");
    });

    it("shows a distinct message when filters produce zero rows", async () => {
      render(<Transactions />);
      await screen.findAllByRole("row");

      await userEvent.type(screen.getByLabelText(/search/i), "nonexistent merchant");

      expect(await screen.findByText(/no Transactions match/i)).toBeInTheDocument();
    });

    it("sorts by Date descending by default", async () => {
      render(<Transactions />);
      await screen.findAllByRole("row");

      expect(rowTexts()[0]).toContain("Fuel stop"); // 2026-09-10, newest
      expect(rowTexts()[2]).toContain("Woolworths"); // 2026-08-05, oldest
    });

    it("toggles Date sort direction on repeated header clicks", async () => {
      render(<Transactions />);
      await screen.findAllByRole("row");

      await userEvent.click(screen.getByRole("button", { name: /date/i }));

      expect(rowTexts()[0]).toContain("Woolworths"); // now oldest-first
    });

    it("sorts by Amount when its header is clicked, without a network refetch", async () => {
      render(<Transactions />);
      await screen.findAllByRole("row");

      const callsBeforeSort = fetchMock.mock.calls.length;
      // Switching sort key keeps the current direction (desc) rather than flipping it.
      await userEvent.click(screen.getByRole("button", { name: /amount/i }));

      expect(rowTexts()[0]).toContain("Employer Pty Ltd"); // $4000, highest first
      expect(fetchMock.mock.calls.length).toBe(callsBeforeSort);
    });

    it("flips Amount sort direction on a second click of its header", async () => {
      render(<Transactions />);
      await screen.findAllByRole("row");

      await userEvent.click(screen.getByRole("button", { name: /amount/i }));
      await userEvent.click(screen.getByRole("button", { name: /amount/i }));

      expect(rowTexts()[0]).toContain("Woolworths"); // $42.50, lowest first
    });
  });
});
