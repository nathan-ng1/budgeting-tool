import { describe, expect, it } from "vitest";

import { gridMonthTotals, gridTotalsByType, leftToBudget, totalsByType } from "./budgetTotals.js";

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

describe("gridMonthTotals", () => {
  it("turns gridTotalsByType's per-Type arrays into one Type totals object per month", () => {
    const totals = { Income: [5000, 0, 5000], Expense: [650, 800, 100] };

    expect(gridMonthTotals(totals, 3)).toEqual([
      { Income: 5000, Expense: 650 },
      { Income: 0, Expense: 800 },
      { Income: 5000, Expense: 100 },
    ]);
  });

  it("counts a Type with no Categories (an empty array) as $0 in every month", () => {
    expect(gridMonthTotals({ Income: [5000, 5000], Debt: [] }, 2)).toEqual([
      { Income: 5000, Debt: 0 },
      { Income: 5000, Debt: 0 },
    ]);
  });
});

describe("leftToBudget", () => {
  it("subtracts every budgeted outflow Type, Savings included, from budgeted Income", () => {
    const totals = { Income: 6000, Expense: 1500, "Bills & Subscriptions": 300, Debt: 2000, Savings: 1000 };

    expect(leftToBudget(totals)).toEqual({ income: 6000, outflows: 4800, left: 1200 });
  });

  it("counts a missing Type as $0", () => {
    expect(leftToBudget({ Income: 5000, Expense: 650 })).toEqual({ income: 5000, outflows: 650, left: 4350 });
    expect(leftToBudget({ Savings: 400 })).toEqual({ income: 0, outflows: 400, left: -400 });
  });

  it("is $0 all round when nothing is budgeted", () => {
    expect(leftToBudget({})).toEqual({ income: 0, outflows: 0, left: 0 });
  });

  it("goes negative when outflows exceed Income", () => {
    expect(leftToBudget({ Income: 3000, Expense: 2000, Debt: 1500 })).toEqual({ income: 3000, outflows: 3500, left: -500 });
  });
});
