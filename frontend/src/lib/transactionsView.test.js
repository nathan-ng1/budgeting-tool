import { describe, expect, it } from "vitest";

import {
  ALL_CATEGORIES,
  ALL_MONTHS,
  ALL_TYPES,
  TYPES,
  categoryOptions,
  monthOptions,
  nextSort,
  pageCount,
  paginate,
  visibleTransactions,
} from "./transactionsView.js";

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

const DEFAULT_FILTERS = { category: ALL_CATEGORIES, month: ALL_MONTHS, type: ALL_TYPES, search: "" };
const DEFAULT_SORT = { sortKey: "date", sortDirection: "desc" };

function view(transactions, filters = {}, sort = {}) {
  return visibleTransactions(transactions, { ...DEFAULT_FILTERS, ...filters }, { ...DEFAULT_SORT, ...sort });
}

describe("categoryOptions", () => {
  it("lists only the Categories actually present in the given Transactions, sorted", () => {
    const transactions = [
      transaction({ category: "Groceries" }),
      transaction({ category: "Transport" }),
      transaction({ category: "Groceries" }),
    ];

    expect(categoryOptions(transactions)).toEqual(["Groceries", "Transport"]);
  });

  it("returns an empty list for no Transactions", () => {
    expect(categoryOptions([])).toEqual([]);
  });
});

describe("monthOptions", () => {
  it("returns the 12 months of the given Financial Year, independent of any Transaction data", () => {
    const months = monthOptions(2026);

    expect(months).toHaveLength(12);
    expect(months[0]).toEqual({ value: "2026-07", label: "Jul" });
    expect(months[11]).toEqual({ value: "2027-06", label: "Jun" });
  });
});

describe("TYPES", () => {
  it("always offers Income, Expense, Debt, Transfer regardless of what Transactions are loaded", () => {
    expect(TYPES).toEqual(["Income", "Expense", "Debt", "Transfer"]);
  });
});

describe("visibleTransactions filtering", () => {
  const transactions = [
    transaction({ id: 1, category: "Groceries", type: "Expense", date: "2026-08-05", notes: "Woolworths" }),
    transaction({ id: 2, category: "Transport", type: "Expense", date: "2026-09-10", notes: "Fuel" }),
    transaction({ id: 3, category: "Salary", type: "Income", date: "2026-08-20", notes: "Employer Pty Ltd" }),
  ];

  it("filters by Category alone", () => {
    expect(view(transactions, { category: "Groceries" }).map((t) => t.id)).toEqual([1]);
  });

  it("filters by Month alone", () => {
    expect(view(transactions, { month: "2026-08" }).map((t) => t.id).sort()).toEqual([1, 3]);
  });

  it("filters by Type alone", () => {
    expect(view(transactions, { type: "Income" }).map((t) => t.id)).toEqual([3]);
  });

  it("ANDs Category, Month, and Type together", () => {
    expect(view(transactions, { category: "Salary", month: "2026-08", type: "Income" }).map((t) => t.id)).toEqual([3]);
    expect(view(transactions, { category: "Salary", month: "2026-09", type: "Income" })).toEqual([]);
  });

  it("matches Notes case-insensitively as a substring", () => {
    expect(view(transactions, { search: "woolworths" }).map((t) => t.id)).toEqual([1]);
    expect(view(transactions, { search: "EMPLOYER" }).map((t) => t.id)).toEqual([3]);
    expect(view(transactions, { search: "pty" }).map((t) => t.id)).toEqual([3]);
  });

  it("combines search with active filters", () => {
    expect(view(transactions, { type: "Expense", search: "fuel" }).map((t) => t.id)).toEqual([2]);
    expect(view(transactions, { type: "Income", search: "fuel" })).toEqual([]);
  });

  it("returns every Transaction when no filters or search are active", () => {
    expect(view(transactions).map((t) => t.id).sort()).toEqual([1, 2, 3]);
  });
});

describe("visibleTransactions sorting", () => {
  const transactions = [
    transaction({ id: 1, date: "2026-08-05", amount: 30 }),
    transaction({ id: 2, date: "2026-08-20", amount: 10 }),
    transaction({ id: 3, date: "2026-07-01", amount: 50 }),
  ];

  it("defaults to Date descending", () => {
    expect(view(transactions).map((t) => t.id)).toEqual([2, 1, 3]);
  });

  it("sorts by Date ascending when asked", () => {
    expect(view(transactions, {}, { sortKey: "date", sortDirection: "asc" }).map((t) => t.id)).toEqual([3, 1, 2]);
  });

  it("sorts by Amount, on the stored positive figure", () => {
    expect(view(transactions, {}, { sortKey: "amount", sortDirection: "asc" }).map((t) => t.id)).toEqual([2, 1, 3]);
    expect(view(transactions, {}, { sortKey: "amount", sortDirection: "desc" }).map((t) => t.id)).toEqual([3, 1, 2]);
  });
});

describe("nextSort", () => {
  it("flips direction when clicking the already-active sort column", () => {
    expect(nextSort({ sortKey: "date", sortDirection: "desc" }, "date")).toEqual({
      sortKey: "date",
      sortDirection: "asc",
    });
    expect(nextSort({ sortKey: "date", sortDirection: "asc" }, "date")).toEqual({
      sortKey: "date",
      sortDirection: "desc",
    });
  });

  it("switches to a newly-clicked column without flipping direction", () => {
    expect(nextSort({ sortKey: "date", sortDirection: "desc" }, "amount")).toEqual({
      sortKey: "amount",
      sortDirection: "desc",
    });
  });
});

describe("pageCount", () => {
  it("divides the total by the page size, rounding up", () => {
    expect(pageCount(25, 10)).toBe(3);
    expect(pageCount(20, 10)).toBe(2);
  });

  it("is always at least 1, even for zero Transactions", () => {
    expect(pageCount(0, 10)).toBe(1);
  });
});

describe("paginate", () => {
  const transactions = [
    transaction({ id: 1 }),
    transaction({ id: 2 }),
    transaction({ id: 3 }),
    transaction({ id: 4 }),
    transaction({ id: 5 }),
  ];

  it("returns the slice for the given page and page size", () => {
    expect(paginate(transactions, 1, 2).map((t) => t.id)).toEqual([1, 2]);
    expect(paginate(transactions, 2, 2).map((t) => t.id)).toEqual([3, 4]);
    expect(paginate(transactions, 3, 2).map((t) => t.id)).toEqual([5]);
  });

  it("returns an empty page past the end of the list", () => {
    expect(paginate(transactions, 4, 2)).toEqual([]);
  });
});
