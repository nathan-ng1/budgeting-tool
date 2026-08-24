import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createTransaction,
  deleteTransaction,
  fetchCategories,
  fetchTransactions,
  updateTransaction,
} from "./transactionsApi.js";

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

const TRANSACTION = { date: "2026-08-05", amount: 42.5, type: "Expense", category: "Groceries", notes: "Woolworths" };

describe("transactionsApi", () => {
  it("lists the Financial Year's transactions", async () => {
    ok([{ id: 1, ...TRANSACTION }]);

    expect(await fetchTransactions({ year: 2026, month: 7 })).toEqual([{ id: 1, ...TRANSACTION }]);
    expect(fetchMock).toHaveBeenCalledWith("/api/transactions?year=2026&month=7", expect.anything());
  });

  it("fetches every Category the form offers", async () => {
    const categories = [{ id: 1, type: "Expense", name: "Groceries", emoji: null, locked: false }];
    ok(categories);

    expect(await fetchCategories()).toEqual(categories);
    expect(fetchMock).toHaveBeenCalledWith("/api/categories", expect.anything());
  });

  it("posts a new transaction and returns what the store made of it", async () => {
    ok({ id: 7, ...TRANSACTION }, 201);

    expect(await createTransaction(TRANSACTION)).toEqual({ id: 7, ...TRANSACTION });

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/transactions");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual(TRANSACTION);
  });

  it("puts an edited transaction to its own id", async () => {
    ok({ id: 7, ...TRANSACTION });

    await updateTransaction(7, TRANSACTION);

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/transactions/7");
    expect(options.method).toBe("PUT");
  });

  it("deletes a transaction by id, and expects no body back", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 204 });

    await deleteTransaction(7);

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/transactions/7");
    expect(options.method).toBe("DELETE");
  });

  it("surfaces the backend's own message when a write is rejected", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ error: "Category 'Salary' is not a valid Expense Category" }),
    });

    await expect(createTransaction(TRANSACTION)).rejects.toThrow("Category 'Salary' is not a valid Expense Category");
  });

  it("falls back to the status when the failure carries no message", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });

    await expect(fetchTransactions({ year: 2026, month: 7 })).rejects.toThrow("500");
  });
});
