import { describe, expect, it } from "vitest";

import { gridTotalsByType, totalsByType } from "./budgetTotals.js";

describe("totalsByType", () => {
  const editor = {
    Income: [{ category: "Salary" }],
    Expense: [{ category: "Groceries" }, { category: "Transport" }],
    Debt: [{ category: "Mortgage Repayment" }],
  };

  it("sums each Type's Categories from the live values map", () => {
    const values = { Salary: "5000", Groceries: "650", Transport: "120", "Mortgage Repayment": "2000" };

    expect(totalsByType(editor, values)).toEqual({ Income: 5000, Expense: 770, Debt: 2000 });
  });

  it("treats a blank or missing field as $0, not NaN", () => {
    const values = { Salary: "", Groceries: "650", Transport: "" };

    expect(totalsByType(editor, values)).toEqual({ Income: 0, Expense: 650, Debt: 0 });
  });
});

describe("gridTotalsByType", () => {
  it("sums each Type's Categories per month column, treating an unset month as $0", () => {
    const grid = {
      Income: [{ category: "Salary", amounts: [5000, null, 5000] }],
      Expense: [
        { category: "Groceries", amounts: [650, 700, null] },
        { category: "Transport", amounts: [null, 100, 100] },
      ],
    };

    expect(gridTotalsByType(grid)).toEqual({
      Income: [5000, 0, 5000],
      Expense: [650, 800, 100],
    });
  });

  it("returns an empty array for a Type with no Categories", () => {
    expect(gridTotalsByType({ Debt: [] })).toEqual({ Debt: [] });
  });
});
