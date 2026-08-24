import { render, screen, waitFor, within } from "@testing-library/react";
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

const CATEGORIES = [
  { id: 1, type: "Expense", name: "Groceries", emoji: null, locked: false },
  { id: 2, type: "Expense", name: "Transport", emoji: null, locked: false },
  { id: 3, type: "Income", name: "Salary", emoji: null, locked: false },
];

/** Answer each endpoint from `transactions`, so the screen reloads real state. */
function backend(transactions = [], categories = CATEGORIES) {
  let stored = [...transactions];
  let nextId = 100;

  return vi.fn(async (url, options = {}) => {
    const method = options.method ?? "GET";

    if (url === "/api/categories") {
      return { ok: true, status: 200, json: async () => categories };
    }
    if (method === "GET") {
      return { ok: true, status: 200, json: async () => stored };
    }
    if (method === "POST") {
      const created = { id: (nextId += 1), ...JSON.parse(options.body) };
      stored = [...stored, created];
      return { ok: true, status: 201, json: async () => created };
    }
    if (method === "PUT") {
      const id = Number(url.split("/").pop());
      const updated = { id, ...JSON.parse(options.body) };
      stored = stored.map((t) => (t.id === id ? updated : t));
      return { ok: true, status: 200, json: async () => updated };
    }
    const id = Number(url.split("/").pop());
    stored = stored.filter((t) => t.id !== id);
    return { ok: true, status: 204 };
  });
}

function useBackend(transactions) {
  fetchMock = backend(transactions);
  vi.stubGlobal("fetch", fetchMock);
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
    expect(headers).toEqual(["Date", "Amount", "Type", "Category", "Notes", ""]);
  });

  it("renders Amount plain, with no colour or sign", async () => {
    respondWith([transaction({ amount: 42.5 })]);
    render(<Transactions />);

    expect(await screen.findByText("$42.50")).toBeInTheDocument();
  });

  it("shows a Category's emoji next to its name, in the table, the filter, and the Category select", async () => {
    fetchMock = backend([transaction({ category: "Groceries" })], [
      { id: 1, type: "Expense", name: "Groceries", emoji: "🛒", locked: false },
      { id: 2, type: "Expense", name: "Transport", emoji: null, locked: false },
      { id: 3, type: "Income", name: "Salary", emoji: null, locked: false },
    ]);
    vi.stubGlobal("fetch", fetchMock);
    render(<Transactions />);
    await screen.findAllByRole("row");

    const [firstDataRow] = screen.getAllByRole("row").slice(1);
    expect(within(firstDataRow).getByText("🛒 Groceries")).toBeInTheDocument();

    const filter = screen.getByLabelText(/category/i);
    expect(within(filter).getByRole("option", { name: "🛒 Groceries" })).toBeInTheDocument();
    expect(within(filter).getByRole("option", { name: "🛒 Groceries" })).toHaveValue("Groceries");

    await userEvent.click(screen.getByRole("button", { name: "Add transaction" }));
    const [categorySelect] = screen.getAllByLabelText("Category");
    expect(within(categorySelect).getByRole("option", { name: "🛒 Groceries" })).toBeInTheDocument();
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

  describe("pagination", () => {
    function transactionsList(count) {
      return Array.from({ length: count }, (_, index) =>
        transaction({
          id: index + 1,
          date: `2026-08-${String((index % 27) + 1).padStart(2, "0")}`,
          notes: `Transaction ${index + 1}`,
          category: "Transport",
        }),
      );
    }

    it("defaults to 20 rows per page and offers a Next control once there's more than one page", async () => {
      respondWith(transactionsList(25));
      render(<Transactions />);
      await screen.findAllByRole("row");

      expect(rowTexts()).toHaveLength(20);
      expect(screen.getByLabelText(/rows per page/i)).toHaveValue("20");
      expect(screen.getByText("Page 1 of 2")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();
      expect(screen.getByRole("button", { name: "Next" })).toBeEnabled();
    });

    it("does not show pagination controls when everything fits on one page", async () => {
      respondWith(transactionsList(5));
      render(<Transactions />);
      await screen.findAllByRole("row");

      expect(screen.queryByText(/Page \d+ of \d+/)).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Next" })).not.toBeInTheDocument();
    });

    it("moves to the next and previous page", async () => {
      respondWith(transactionsList(25));
      render(<Transactions />);
      await screen.findAllByRole("row");

      await userEvent.click(screen.getByRole("button", { name: "Next" }));

      expect(rowTexts()).toHaveLength(5);
      expect(screen.getByText("Page 2 of 2")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();

      await userEvent.click(screen.getByRole("button", { name: "Previous" }));

      expect(rowTexts()).toHaveLength(20);
      expect(screen.getByText("Page 1 of 2")).toBeInTheDocument();
    });

    it("changes how many rows are shown via the Rows per page dropdown", async () => {
      respondWith(transactionsList(25));
      render(<Transactions />);
      await screen.findAllByRole("row");

      await userEvent.selectOptions(screen.getByLabelText(/rows per page/i), "10");

      expect(rowTexts()).toHaveLength(10);
      expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
    });

    it("returns to page 1 when a filter narrows the list below the current page", async () => {
      const transactions = transactionsList(25);
      transactions[0] = { ...transactions[0], category: "Groceries" };
      respondWith(transactions);
      render(<Transactions />);
      await screen.findAllByRole("row");

      await userEvent.click(screen.getByRole("button", { name: "Next" }));
      expect(screen.getByText("Page 2 of 2")).toBeInTheDocument();

      await userEvent.selectOptions(screen.getByLabelText(/category/i), "Groceries");

      expect(rowTexts()).toHaveLength(1);
      expect(screen.queryByText(/Page \d+ of \d+/)).not.toBeInTheDocument();
    });
  });

  describe("adding, editing, and deleting", () => {
    it("adds a transaction and shows it in the list without a reload", async () => {
      useBackend([]);
      render(<Transactions />);
      await userEvent.click(await screen.findByRole("button", { name: "Add transaction" }));

      await userEvent.clear(screen.getByLabelText("Date"));
      await userEvent.type(screen.getByLabelText("Date"), "2026-08-05");
      await userEvent.type(screen.getByLabelText("Amount"), "42.50");
      await userEvent.selectOptions(screen.getByLabelText("Category"), "Groceries");
      await userEvent.type(screen.getByLabelText("Notes"), "Woolworths");
      await userEvent.click(screen.getByRole("button", { name: "Save transaction" }));

      expect(await screen.findByText("Woolworths")).toBeInTheDocument();

      const posted = fetchMock.mock.calls.find(([, options]) => options?.method === "POST");
      expect(JSON.parse(posted[1].body)).toMatchObject({
        date: "2026-08-05",
        amount: 42.5,
        type: "Expense",
        category: "Groceries",
        notes: "Woolworths",
      });
    });

    it("offers only the Categories that belong to the chosen Type when adding", async () => {
      useBackend([]);
      render(<Transactions />);
      await userEvent.click(await screen.findByRole("button", { name: "Add transaction" }));

      const category = screen.getByLabelText("Category");
      expect(within(category).getByRole("option", { name: "Groceries" })).toBeInTheDocument();

      await userEvent.selectOptions(screen.getByLabelText("Type"), "Income");

      expect(within(category).queryByRole("option", { name: "Groceries" })).not.toBeInTheDocument();
      expect(within(category).getByRole("option", { name: "Salary" })).toBeInTheDocument();
    });

    it("shows the store's own rejection and keeps the add form open to fix it", async () => {
      useBackend([]);
      render(<Transactions />);
      await userEvent.click(await screen.findByRole("button", { name: "Add transaction" }));
      fetchMock.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: "Category 'Salary' is not a valid Expense Category" }),
      });

      await userEvent.clear(screen.getByLabelText("Date"));
      await userEvent.type(screen.getByLabelText("Date"), "2026-08-05");
      await userEvent.type(screen.getByLabelText("Amount"), "42.50");
      await userEvent.selectOptions(screen.getByLabelText("Category"), "Groceries");
      await userEvent.type(screen.getByLabelText("Notes"), "Woolworths");
      await userEvent.click(screen.getByRole("button", { name: "Save transaction" }));

      expect(await screen.findByRole("alert")).toHaveTextContent("not a valid Expense Category");
      expect(screen.getByLabelText("Notes")).toHaveValue("Woolworths");
    });

    it("cancelling the add form discards it without saving", async () => {
      useBackend([]);
      render(<Transactions />);
      await userEvent.click(await screen.findByRole("button", { name: "Add transaction" }));
      await userEvent.type(screen.getByLabelText("Notes"), "Discard me");

      await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

      expect(screen.queryByLabelText("Notes")).not.toBeInTheDocument();
      expect(fetchMock.mock.calls.some(([, options]) => options?.method === "POST")).toBe(false);
    });

    it("edits an existing transaction in place", async () => {
      useBackend([transaction()]);
      render(<Transactions />);

      await userEvent.click(await screen.findByRole("button", { name: "Edit Woolworths" }));

      const amount = screen.getByLabelText("Amount");
      expect(amount).toHaveValue(42.5);

      await userEvent.clear(amount);
      await userEvent.type(amount, "50");
      await userEvent.click(screen.getByRole("button", { name: "Save" }));

      const put = await waitFor(() => {
        const call = fetchMock.mock.calls.find(([, options]) => options?.method === "PUT");
        expect(call).toBeTruthy();
        return call;
      });
      expect(put[0]).toBe("/api/transactions/1");
      expect(JSON.parse(put[1].body).amount).toBe(50);
      expect(await screen.findByText("$50.00")).toBeInTheDocument();
    });

    it("cancelling an edit discards it and keeps the original row", async () => {
      useBackend([transaction()]);
      render(<Transactions />);

      await userEvent.click(await screen.findByRole("button", { name: "Edit Woolworths" }));
      await userEvent.clear(screen.getByLabelText("Amount"));
      await userEvent.type(screen.getByLabelText("Amount"), "999");
      await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

      expect(screen.queryByLabelText("Amount")).not.toBeInTheDocument();
      expect(await screen.findByText("$42.50")).toBeInTheDocument();
      expect(fetchMock.mock.calls.some(([, options]) => options?.method === "PUT")).toBe(false);
    });

    it("shows the store's own rejection on an edit and leaves the row editable", async () => {
      useBackend([transaction()]);
      render(<Transactions />);
      await userEvent.click(await screen.findByRole("button", { name: "Edit Woolworths" }));
      fetchMock.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: "Category 'Salary' is not a valid Expense Category" }),
      });

      await userEvent.click(screen.getByRole("button", { name: "Save" }));

      expect(await screen.findByRole("alert")).toHaveTextContent("not a valid Expense Category");
      expect(screen.getByLabelText("Amount")).toBeInTheDocument();
    });

    it("requires an inline confirm before deleting a transaction", async () => {
      useBackend([transaction()]);
      render(<Transactions />);

      await userEvent.click(await screen.findByRole("button", { name: "Delete Woolworths" }));

      expect(screen.getByText("Woolworths")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Confirm delete?" })).toBeInTheDocument();
      expect(fetchMock.mock.calls.some(([, options]) => options?.method === "DELETE")).toBe(false);
    });

    it("cancelling a delete confirmation leaves the row in place", async () => {
      useBackend([transaction()]);
      render(<Transactions />);
      await userEvent.click(await screen.findByRole("button", { name: "Delete Woolworths" }));

      await userEvent.click(screen.getByRole("button", { name: "Cancel" }));

      expect(screen.getByText("Woolworths")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Edit Woolworths" })).toBeInTheDocument();
    });

    it("deletes a transaction only after the confirm step, dropping it from the list", async () => {
      useBackend([transaction()]);
      render(<Transactions />);
      await userEvent.click(await screen.findByRole("button", { name: "Delete Woolworths" }));

      await userEvent.click(screen.getByRole("button", { name: "Confirm delete?" }));

      await waitFor(() => expect(screen.queryByText("Woolworths")).not.toBeInTheDocument());
      expect(
        fetchMock.mock.calls.some(([url, options]) => url === "/api/transactions/1" && options?.method === "DELETE"),
      ).toBe(true);
    });
  });
});
