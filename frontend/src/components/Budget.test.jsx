import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Budget from "./Budget.jsx";

function editor(overrides = {}) {
  return {
    Income: [{ category: "Salary", amount: null }],
    Expense: [
      { category: "Groceries", amount: 650 },
      { category: "Dining & Takeaway", amount: null },
    ],
    Debt: [{ category: "Mortgage Repayment", amount: null }],
    ...overrides,
  };
}

function blankEditor() {
  return {
    Income: [{ category: "Salary", amount: null }],
    Expense: [
      { category: "Groceries", amount: null },
      { category: "Dining & Takeaway", amount: null },
    ],
    Debt: [{ category: "Mortgage Repayment", amount: null }],
  };
}

function updateCategory(state, category, amount) {
  for (const rows of Object.values(state)) {
    const row = rows.find((r) => r.category === category);
    if (row) {
      row.amount = amount;
    }
  }
}

/** Answers /api/budget-editor keyed by (year, month), so a save round-trips
 * through a real GET/PUT/DELETE cycle the way the real backend would. */
function backend(initial = editor()) {
  const byMonth = new Map([["2026-8", structuredClone(initial)]]);

  return vi.fn(async (url, options = {}) => {
    const method = options.method ?? "GET";
    const parsed = new URL(url, "http://localhost");
    const year = parsed.searchParams.get("year");
    const month = parsed.searchParams.get("month");
    const key = `${year}-${month}`;

    if (parsed.pathname === "/api/budget-editor") {
      if (!byMonth.has(key)) {
        byMonth.set(key, blankEditor());
      }
      return { ok: true, status: 200, json: async () => byMonth.get(key) };
    }

    const match = parsed.pathname.match(/^\/api\/budget-editor\/(.+)$/);
    const category = decodeURIComponent(match[1]);
    const state = byMonth.get(key) ?? blankEditor();
    byMonth.set(key, state);

    if (method === "PUT") {
      const { amount } = JSON.parse(options.body);
      updateCategory(state, category, amount);
      return { ok: true, status: 200, json: async () => ({ category, amount }) };
    }

    updateCategory(state, category, null);
    return { ok: true, status: 204 };
  });
}

let fetchMock;

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date(2026, 7, 21)); // 21 August 2026
  fetchMock = backend();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function useBackend(initial) {
  fetchMock = backend(initial);
  vi.stubGlobal("fetch", fetchMock);
}

describe("Budget", () => {
  it("opens on the current month, showing every Category grouped by Type", async () => {
    render(<Budget />);

    expect(await screen.findByText("Salary")).toBeInTheDocument();
    expect(screen.getByText("Groceries")).toBeInTheDocument();
    expect(screen.getByText("Mortgage Repayment")).toBeInTheDocument();
    expect(screen.getByText("Income")).toBeInTheDocument();
    expect(screen.getByText("Expense")).toBeInTheDocument();
    expect(screen.getByText("Debt")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aug" })).toHaveAttribute("aria-pressed", "true");
  });

  it("shows a set Category Budget's Amount, and blank for an unset one", async () => {
    render(<Budget />);

    expect(await screen.findByLabelText("Groceries Budgeted Amount")).toHaveValue(650);
    expect(screen.getByLabelText("Salary Budgeted Amount")).toHaveValue(null);
  });

  it("renders a month with no Category Budgets set as an all-blank table, not an error", async () => {
    useBackend(editor({ Expense: [{ category: "Groceries", amount: null }] }));
    render(<Budget />);

    expect(await screen.findByLabelText("Groceries Budgeted Amount")).toHaveValue(null);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("has no Full year pill - only the twelve months", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    expect(screen.queryByRole("button", { name: "Full year" })).not.toBeInTheDocument();
  });

  it("does not persist an edit until Save is clicked", async () => {
    render(<Budget />);
    const salary = await screen.findByLabelText("Salary Budgeted Amount");

    await userEvent.type(salary, "5000");

    expect(fetchMock.mock.calls.some(([, options]) => options?.method === "PUT")).toBe(false);
  });

  it("disables Save until something changes", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    expect(screen.getByRole("button", { name: "Save budgets" })).toBeDisabled();

    await userEvent.type(screen.getByLabelText("Salary Budgeted Amount"), "5000");

    expect(screen.getByRole("button", { name: "Save budgets" })).toBeEnabled();
  });

  it("saves an edited Amount as an upsert for that Category and month", async () => {
    render(<Budget />);
    const salary = await screen.findByLabelText("Salary Budgeted Amount");

    await userEvent.type(salary, "5000");
    await userEvent.click(screen.getByRole("button", { name: "Save budgets" }));

    const put = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === "PUT");
      expect(call).toBeTruthy();
      return call;
    });
    expect(put[0]).toBe("/api/budget-editor/Salary?year=2026&month=8");
    expect(JSON.parse(put[1].body)).toEqual({ amount: 5000 });
  });

  it("clearing a set field back to blank and saving deletes that Category's Category Budget", async () => {
    render(<Budget />);
    const groceries = await screen.findByLabelText("Groceries Budgeted Amount");

    await userEvent.clear(groceries);
    await userEvent.click(screen.getByRole("button", { name: "Save budgets" }));

    const del = await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, options]) => options?.method === "DELETE");
      expect(call).toBeTruthy();
      return call;
    });
    expect(del[0]).toBe("/api/budget-editor/Groceries?year=2026&month=8");
  });

  it("only writes the Categories that actually changed, not every row", async () => {
    render(<Budget />);
    await userEvent.type(await screen.findByLabelText("Salary Budgeted Amount"), "5000");

    await userEvent.click(screen.getByRole("button", { name: "Save budgets" }));

    await waitFor(() => expect(fetchMock.mock.calls.some(([, o]) => o?.method === "PUT")).toBe(true));
    const writes = fetchMock.mock.calls.filter(([, o]) => o?.method === "PUT" || o?.method === "DELETE");
    expect(writes).toHaveLength(1);
  });

  it("reflects saved values after Save, sourced from what the store actually holds", async () => {
    render(<Budget />);
    await userEvent.type(await screen.findByLabelText("Salary Budgeted Amount"), "5000");
    await userEvent.click(screen.getByRole("button", { name: "Save budgets" }));

    expect(await screen.findByLabelText("Salary Budgeted Amount")).toHaveValue(5000);
    expect(screen.getByRole("button", { name: "Save budgets" })).toBeDisabled();
  });

  it("switching months loads that month's own Category Budgets independently", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    await userEvent.click(screen.getByRole("button", { name: "Sep" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/budget-editor?year=2026&month=9", expect.anything()),
    );
    expect(await screen.findByLabelText("Groceries Budgeted Amount")).toHaveValue(null);
  });

  it("surfaces a load failure instead of an empty table", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });
    render(<Budget />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/500/);
  });

  it("surfaces the store's own rejection on Save and keeps the edit on screen", async () => {
    render(<Budget />);
    const salary = await screen.findByLabelText("Salary Budgeted Amount");
    await userEvent.type(salary, "5000");

    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ error: "Category 'Salary' is not a valid Category" }),
    });
    await userEvent.click(screen.getByRole("button", { name: "Save budgets" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("not a valid Category");
    expect(screen.getByLabelText("Salary Budgeted Amount")).toHaveValue(5000);
  });
});
