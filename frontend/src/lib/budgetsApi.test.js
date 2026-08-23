import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { deleteCategoryBudget, fetchBudgetEditor, fetchBudgetGrid, saveCategoryBudget } from "./budgetsApi.js";

let fetchMock;

beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function ok(body, status = 200) {
  fetchMock.mockResolvedValue({ ok: true, status, json: async () => body });
}

describe("budgetsApi", () => {
  it("fetches the editor for one (year, month)", async () => {
    ok({ Income: [], Expense: [], Debt: [] });

    expect(await fetchBudgetEditor({ year: 2026, month: 8 })).toEqual({ Income: [], Expense: [], Debt: [] });
    expect(fetchMock).toHaveBeenCalledWith("/api/budget-editor?year=2026&month=8", expect.anything());
  });

  it("includes the trailing window in the query when provided", async () => {
    ok({ Income: [], Expense: [], Debt: [] });

    await fetchBudgetEditor({ year: 2026, month: 8 }, { window: 12 });

    expect(fetchMock).toHaveBeenCalledWith("/api/budget-editor?year=2026&month=8&window=12", expect.anything());
  });

  it("saves a Category Budget with a PUT to that Category's own path", async () => {
    ok({ category: "Groceries", amount: 650 });

    await saveCategoryBudget({ year: 2026, month: 8 }, "Groceries", 650);

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/budget-editor/Groceries?year=2026&month=8");
    expect(options.method).toBe("PUT");
    expect(JSON.parse(options.body)).toEqual({ amount: 650 });
  });

  it("encodes a Category with special characters into the URL", async () => {
    ok({ category: "Dining & Takeaway", amount: 300 });

    await saveCategoryBudget({ year: 2026, month: 8 }, "Dining & Takeaway", 300);

    const [url] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/budget-editor/Dining%20%26%20Takeaway?year=2026&month=8");
  });

  it("deletes a Category Budget, and expects no body back", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 204 });

    await deleteCategoryBudget({ year: 2026, month: 8 }, "Groceries");

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/budget-editor/Groceries?year=2026&month=8");
    expect(options.method).toBe("DELETE");
  });

  it("surfaces the backend's own message when a save is rejected", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ error: "Category 'NotACategory' is not a valid Category" }),
    });

    await expect(saveCategoryBudget({ year: 2026, month: 8 }, "NotACategory", 100)).rejects.toThrow(
      "Category 'NotACategory' is not a valid Category",
    );
  });

  it("falls back to the status when the failure carries no message", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });

    await expect(fetchBudgetEditor({ year: 2026, month: 8 })).rejects.toThrow("500");
  });

  it("fetches the Full year grid for one Financial Year", async () => {
    ok({ Income: [], Expense: [], Debt: [] });

    expect(await fetchBudgetGrid(2026)).toEqual({ Income: [], Expense: [], Debt: [] });
    expect(fetchMock).toHaveBeenCalledWith("/api/budget-grid?year=2026", expect.anything());
  });
});
