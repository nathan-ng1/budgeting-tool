import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createRecurringRule,
  deleteRecurringRule,
  fetchCategories,
  fetchRecurringRules,
  updateRecurringRule,
} from "./recurringApi.js";

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

const RULE = { amount: 100, type: "Expense", category: "Subscriptions", frequency: "Weekly" };

describe("recurringApi", () => {
  it("lists the rules the endpoint returns", async () => {
    ok([{ id: 1, ...RULE }]);

    expect(await fetchRecurringRules()).toEqual([{ id: 1, ...RULE }]);
    expect(fetchMock).toHaveBeenCalledWith("/api/recurring-rules", expect.anything());
  });

  it("fetches the valid Type/Category pairs the form offers", async () => {
    ok({ Expense: ["Subscriptions"], Income: ["Salary"] });

    expect(await fetchCategories()).toEqual({ Expense: ["Subscriptions"], Income: ["Salary"] });
    expect(fetchMock).toHaveBeenCalledWith("/api/categories", expect.anything());
  });

  it("posts a new rule and returns what the store made of it", async () => {
    ok({ id: 7, ...RULE }, 201);

    expect(await createRecurringRule(RULE)).toEqual({ id: 7, ...RULE });

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/recurring-rules");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual(RULE);
  });

  it("puts an edited rule to its own id", async () => {
    ok({ id: 7, ...RULE });

    await updateRecurringRule(7, RULE);

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/recurring-rules/7");
    expect(options.method).toBe("PUT");
  });

  it("deletes a rule by id, and expects no body back", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 204 });

    await deleteRecurringRule(7);

    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/recurring-rules/7");
    expect(options.method).toBe("DELETE");
  });

  it("surfaces the backend's own message when a write is rejected", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ error: "Category 'Salary' is not a valid Expense Category" }),
    });

    await expect(createRecurringRule(RULE)).rejects.toThrow("Category 'Salary' is not a valid Expense Category");
  });

  it("falls back to the status when the failure carries no message", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 500, json: async () => ({}) });

    await expect(fetchRecurringRules()).rejects.toThrow("500");
  });
});
