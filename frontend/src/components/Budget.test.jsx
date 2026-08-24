import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Budget from "./Budget.jsx";

function row(overrides = {}) {
  return {
    category: "Groceries",
    amount: null,
    last_month_actual: 0,
    last_month_budgeted: null,
    trailing_average_actual: null,
    average_variance_pct: null,
    ...overrides,
  };
}

function editor(overrides = {}) {
  return {
    Income: [row({ category: "Salary" })],
    Expense: [
      row({
        category: "Groceries",
        amount: 650,
        last_month_actual: 620,
        last_month_budgeted: 600,
        trailing_average_actual: 590.25,
        average_variance_pct: 12.3,
      }),
      row({ category: "Dining & Takeaway" }),
    ],
    Debt: [row({ category: "Mortgage Repayment" })],
    ...overrides,
  };
}

function blankEditor() {
  return {
    Income: [row({ category: "Salary" })],
    Expense: [row({ category: "Groceries" }), row({ category: "Dining & Takeaway" })],
    Debt: [row({ category: "Mortgage Repayment" })],
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

// Full year's July-to-June column order (see financialYear.js) - the fake
// backend derives /api/budget-grid from the same byMonth state PUT/DELETE
// write to, so a value saved via a month pill is provably the same data the
// grid reads back, not two independently-maintained fakes.
const FY_MONTHS = [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6];

function blankGrid() {
  return {
    Income: [{ category: "Salary", amounts: Array(12).fill(null) }],
    Expense: [
      { category: "Groceries", amounts: Array(12).fill(null) },
      { category: "Dining & Takeaway", amounts: Array(12).fill(null) },
    ],
    Debt: [{ category: "Mortgage Repayment", amounts: Array(12).fill(null) }],
  };
}

function gridFromByMonth(byMonth) {
  const grid = blankGrid();
  for (const [type, rows] of Object.entries(grid)) {
    for (const row of rows) {
      row.amounts = FY_MONTHS.map((month) => {
        const year = month >= 7 ? 2026 : 2027;
        const monthEditor = byMonth.get(`${year}-${month}`);
        const monthRow = monthEditor?.[type]?.find((r) => r.category === row.category);
        return monthRow?.amount ?? null;
      });
    }
  }
  return grid;
}

/** Answers /api/budget-editor keyed by (year, month), /api/budget-grid, and
 * /api/budget-suggestion, all sourced from the same byMonth state - so a save
 * round-trips through a real GET/PUT/DELETE cycle, and the Full year grid
 * provably reflects it. */
function backend(initial = editor(), suggestion = { write_up: null, generated_at: null }) {
  const byMonth = new Map([["2026-8", structuredClone(initial)]]);

  return vi.fn(async (url, options = {}) => {
    const method = options.method ?? "GET";
    const parsed = new URL(url, "http://localhost");
    const year = parsed.searchParams.get("year");
    const month = parsed.searchParams.get("month");
    const key = `${year}-${month}`;

    if (parsed.pathname === "/api/budget-suggestion") {
      return { ok: true, status: 200, json: async () => suggestion };
    }

    if (parsed.pathname === "/api/budget-grid") {
      return { ok: true, status: 200, json: async () => gridFromByMonth(byMonth) };
    }

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

function useBackend(initial, suggestion) {
  fetchMock = backend(initial, suggestion);
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

  it("shows each Category's historical context columns, greyed out from the editable Budgeted column", async () => {
    render(<Budget />);
    await screen.findByText("Groceries");

    const groceriesRow = screen.getByText("Groceries").closest("tr");
    const cells = within(groceriesRow).getAllByRole("cell");

    expect(cells[1]).toHaveTextContent("$620"); // last month actual
    expect(cells[1]).toHaveClass("muted");
    expect(cells[2]).toHaveTextContent("$590"); // trailing average actual
    expect(cells[2]).toHaveClass("muted");
    expect(cells[3]).toHaveTextContent("+12%"); // average variance %
    expect(cells[3]).toHaveClass("muted");
    expect(cells[4]).not.toHaveClass("muted"); // the editable Budgeted cell
  });

  it("shows an unset historical column as a dash, not $0", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    const salaryRow = screen.getByText("Salary").closest("tr");
    const cells = within(salaryRow).getAllByRole("cell");

    expect(cells[2]).toHaveTextContent("—"); // trailing average actual, unset
    expect(cells[3]).toHaveTextContent("—"); // average variance %, unset
  });

  it("defaults the trailing window dropdown to 3 months", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    expect(screen.getByLabelText("Trailing window")).toHaveValue("3");
  });

  it("requests the newly selected trailing window from the backend", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    await userEvent.selectOptions(screen.getByLabelText("Trailing window"), "12");

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/budget-editor?year=2026&month=8&window=12", expect.anything()),
    );
  });

  it("changing the trailing window does not discard an unsaved Budgeted edit", async () => {
    render(<Budget />);
    const salary = await screen.findByLabelText("Salary Budgeted Amount");

    await userEvent.type(salary, "5000");
    await userEvent.selectOptions(screen.getByLabelText("Trailing window"), "6");

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/api/budget-editor?year=2026&month=8&window=6", expect.anything()),
    );
    expect(screen.getByLabelText("Salary Budgeted Amount")).toHaveValue(5000);
  });

  it("renders a month with no Category Budgets set as an all-blank table, not an error", async () => {
    useBackend(editor({ Expense: [row({ category: "Groceries" })] }));
    render(<Budget />);

    expect(await screen.findByLabelText("Groceries Budgeted Amount")).toHaveValue(null);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("offers a Full year pill alongside the twelve months", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    expect(screen.getByRole("button", { name: "Full year" })).toBeInTheDocument();
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
      expect(fetchMock).toHaveBeenCalledWith("/api/budget-editor?year=2026&month=9&window=3", expect.anything()),
    );
    expect(await screen.findByLabelText("Groceries Budgeted Amount")).toHaveValue(null);
  });

  it("surfaces a load failure instead of an empty table", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });
    render(<Budget />);

    // The Budget Suggestion fetch fails the same way, so both it and the
    // editor surface their own alert - assert on the editor's specifically.
    const alerts = await screen.findAllByRole("alert");
    expect(alerts.some((alert) => alert.textContent.includes("500"))).toBe(true);
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

  it("shows a Total row per Type, summing that Type's Budgeted Amount column", async () => {
    render(<Budget />);
    await screen.findByText("Groceries");

    const expenseTotalRow = screen.getAllByText("Total")[1].closest("tr");
    // Groceries (650) + Dining & Takeaway (unset, $0).
    expect(expenseTotalRow).toHaveTextContent("$650");
  });

  it("recalculates the Total row live as an input changes, before Save", async () => {
    render(<Budget />);
    const groceries = await screen.findByLabelText("Groceries Budgeted Amount");

    await userEvent.clear(groceries);
    await userEvent.type(groceries, "700");

    const expenseTotalRow = screen.getAllByText("Total")[1].closest("tr");
    expect(expenseTotalRow).toHaveTextContent("$700");
  });

  it("offers an Auto-populate control next to Save budgets, closed by default", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    expect(screen.getByRole("button", { name: "Auto-populate" })).toBeInTheDocument();
    expect(screen.queryByRole("menuitem")).not.toBeInTheDocument();
  });

  it("opens a menu offering Last actuals and Last budgeted", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    await userEvent.click(screen.getByRole("button", { name: "Auto-populate" }));

    expect(screen.getByRole("menuitem", { name: "Last actuals" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Last budgeted" })).toBeInTheDocument();
  });

  it("Last actuals overwrites every Category's field with last month's actual, including an explicit $0", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    await userEvent.click(screen.getByRole("button", { name: "Auto-populate" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Last actuals" }));

    expect(screen.getByLabelText("Salary Budgeted Amount")).toHaveValue(0);
    expect(screen.getByLabelText("Groceries Budgeted Amount")).toHaveValue(620);
    expect(screen.getByLabelText("Dining & Takeaway Budgeted Amount")).toHaveValue(0);
    // Overwrites even an already-set field.
    expect(screen.queryByRole("menuitem")).not.toBeInTheDocument();
  });

  it("Last budgeted overwrites every Category's field with last month's Category Budget, clearing an unset one to blank", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    await userEvent.click(screen.getByRole("button", { name: "Auto-populate" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Last budgeted" }));

    expect(screen.getByLabelText("Salary Budgeted Amount")).toHaveValue(null);
    expect(screen.getByLabelText("Groceries Budgeted Amount")).toHaveValue(600);
  });

  it("does not persist an Auto-populate choice until Save is clicked", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    await userEvent.click(screen.getByRole("button", { name: "Auto-populate" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Last actuals" }));

    expect(fetchMock.mock.calls.some(([, options]) => options?.method === "PUT")).toBe(false);
  });

  it("enables Save once an Auto-populate choice has changed a value", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    await userEvent.click(screen.getByRole("button", { name: "Auto-populate" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Last actuals" }));

    expect(screen.getByRole("button", { name: "Save budgets" })).toBeEnabled();
  });
});

describe("Budget Full year", () => {
  it("shows a read-only grid of every Category by Type against the Financial Year's 12 months", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    await userEvent.click(screen.getByRole("button", { name: "Full year" }));

    expect(await screen.findByRole("columnheader", { name: "Jul" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Jun" })).toBeInTheDocument();
    const groceriesRow = screen.getByText("Groceries").closest("tr");
    // Aug (index 1 of Jul-Jun) carries the seeded $650 Groceries budget.
    expect(within(groceriesRow).getAllByRole("cell")[2]).toHaveTextContent("$650");
  });

  it("shows a blank cell, not a placeholder, for an unset month", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    await userEvent.click(screen.getByRole("button", { name: "Full year" }));
    await screen.findByText("Groceries");

    const salaryRow = screen.getByText("Salary").closest("tr");
    const cells = within(salaryRow).getAllByRole("cell");
    for (const cell of cells.slice(1)) {
      expect(cell).toHaveTextContent("");
    }
  });

  it("offers no editing surface in the Full year grid - no inputs, no Save button, no trailing window", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    await userEvent.click(screen.getByRole("button", { name: "Full year" }));
    await screen.findByText("Groceries");

    expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save budgets" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Trailing window")).not.toBeInTheDocument();
  });

  it("reflects a Category Budget saved via a month pill without a page reload", async () => {
    render(<Budget />);
    const salary = await screen.findByLabelText("Salary Budgeted Amount");

    await userEvent.type(salary, "5000");
    await userEvent.click(screen.getByRole("button", { name: "Save budgets" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([, o]) => o?.method === "PUT")).toBe(true));

    await userEvent.click(screen.getByRole("button", { name: "Full year" }));
    await screen.findByText("Groceries");

    const salaryRow = screen.getByText("Salary").closest("tr");
    // Aug is index 1 of the Jul-Jun columns.
    expect(within(salaryRow).getAllByRole("cell")[2]).toHaveTextContent("$5,000");
  });

  it("marks the Full year pill pressed, and only that one, while it is selected", async () => {
    render(<Budget />);
    await screen.findByText("Salary");

    await userEvent.click(screen.getByRole("button", { name: "Full year" }));

    expect(await screen.findByRole("button", { name: "Full year" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Aug" })).toHaveAttribute("aria-pressed", "false");
  });

  it("surfaces a Full year load failure instead of an empty grid", async () => {
    render(<Budget />);
    await screen.findByText("Salary");
    fetchMock.mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });

    await userEvent.click(screen.getByRole("button", { name: "Full year" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/500/);
  });

  it("shows a Total row per Type, summing each month's Category Budgets", async () => {
    render(<Budget />);
    const salary = await screen.findByLabelText("Salary Budgeted Amount");

    // Give Salary (Income) a value too, so Aug's Expense and Income totals differ.
    await userEvent.type(salary, "5000");
    await userEvent.click(screen.getByRole("button", { name: "Save budgets" }));
    await waitFor(() => expect(fetchMock.mock.calls.some(([, o]) => o?.method === "PUT")).toBe(true));

    await userEvent.click(screen.getByRole("button", { name: "Full year" }));
    await screen.findByText("Groceries");

    const expenseTotalRow = screen.getAllByText("Total")[1].closest("tr");
    // Aug is index 1 of the Jul-Jun columns; Groceries' seeded $650 is the
    // only Expense Category Budget set anywhere in the Financial Year.
    expect(within(expenseTotalRow).getAllByRole("cell")[2]).toHaveTextContent("$650");
    const incomeTotalRow = screen.getAllByText("Total")[0].closest("tr");
    expect(within(incomeTotalRow).getAllByRole("cell")[2]).toHaveTextContent("$5,000");
  });
});

describe("Budget Suggestion", () => {
  it("renders the stored write-up in its own card above the table", async () => {
    useBackend(editor(), { write_up: "Groceries has run over budget.", generated_at: "2026-08-20T14:32:00" });
    render(<Budget />);

    expect(await screen.findByText("Groceries has run over budget.")).toBeInTheDocument();
  });

  it("shows a coherent empty state when no write-up has ever been generated", async () => {
    render(<Budget />); // default backend() seeds { write_up: null }
    await screen.findByText("Salary");

    expect(await screen.findByText(/No Budget Suggestion yet/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows the same write-up whichever month pill is selected", async () => {
    useBackend(editor(), { write_up: "Standing advice.", generated_at: "2026-08-20T14:32:00" });
    render(<Budget />);
    await screen.findByText("Standing advice.");

    await userEvent.click(screen.getByRole("button", { name: "Sep" }));

    expect(await screen.findByText("Standing advice.")).toBeInTheDocument();
  });

  it("shows the same write-up when Full year is selected", async () => {
    useBackend(editor(), { write_up: "Standing advice.", generated_at: "2026-08-20T14:32:00" });
    render(<Budget />);
    await screen.findByText("Standing advice.");

    await userEvent.click(screen.getByRole("button", { name: "Full year" }));

    expect(await screen.findByText("Standing advice.")).toBeInTheDocument();
  });
});
