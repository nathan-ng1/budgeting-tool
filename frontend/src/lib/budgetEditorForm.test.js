import { describe, expect, it } from "vitest";

import { autoPopulatedValuesFrom, changesFrom, valuesFrom } from "./budgetEditorForm.js";

const EDITOR = {
  Income: [{ category: "Salary", amount: 5000 }],
  Expense: [
    { category: "Groceries", amount: 650 },
    { category: "Transport", amount: null },
  ],
  Debt: [{ category: "Mortgage Repayment", amount: null }],
};

describe("valuesFrom", () => {
  it("flattens every Category across every Type into a category -> string map", () => {
    expect(valuesFrom(EDITOR)).toEqual({
      Salary: "5000",
      Groceries: "650",
      Transport: "",
      "Mortgage Repayment": "",
    });
  });

  it("renders an unset Category Budget as an empty string, not '0' or 'null'", () => {
    expect(valuesFrom({ Expense: [{ category: "Groceries", amount: null }] })).toEqual({ Groceries: "" });
  });
});

const EDITOR_WITH_HISTORY = {
  Income: [{ category: "Salary", amount: 5000, last_month_actual: 5200, last_month_budgeted: 5000 }],
  Expense: [
    { category: "Groceries", amount: 650, last_month_actual: 0, last_month_budgeted: null },
    { category: "Transport", amount: null, last_month_actual: 120, last_month_budgeted: 100 },
  ],
};

describe("autoPopulatedValuesFrom", () => {
  it("flattens every Category's last month actual into a category -> string map, mirrored exactly including $0", () => {
    expect(autoPopulatedValuesFrom(EDITOR_WITH_HISTORY, "actual")).toEqual({
      Salary: "5200",
      Groceries: "0",
      Transport: "120",
    });
  });

  it("flattens every Category's last month Category Budget, clearing an unset one to blank rather than skipping it", () => {
    expect(autoPopulatedValuesFrom(EDITOR_WITH_HISTORY, "budgeted")).toEqual({
      Salary: "5000",
      Groceries: "",
      Transport: "100",
    });
  });
});

describe("changesFrom", () => {
  const initial = { Salary: "5000", Groceries: "650", Transport: "", "Mortgage Repayment": "" };

  it("reports nothing changed when values equal initial", () => {
    expect(changesFrom(initial, { ...initial })).toEqual([]);
  });

  it("reports an edited field as an amount change", () => {
    const changes = changesFrom(initial, { ...initial, Groceries: "700" });

    expect(changes).toEqual([{ category: "Groceries", amount: 700 }]);
  });

  it("reports a newly-filled blank field as an amount change", () => {
    const changes = changesFrom(initial, { ...initial, Transport: "120" });

    expect(changes).toEqual([{ category: "Transport", amount: 120 }]);
  });

  it("reports a field cleared back to blank as a delete (amount null)", () => {
    const changes = changesFrom(initial, { ...initial, Groceries: "" });

    expect(changes).toEqual([{ category: "Groceries", amount: null }]);
  });

  it("reports every changed field when several change at once", () => {
    const changes = changesFrom(initial, { ...initial, Groceries: "700", Transport: "120" });

    expect(changes).toEqual(
      expect.arrayContaining([
        { category: "Groceries", amount: 700 },
        { category: "Transport", amount: 120 },
      ]),
    );
    expect(changes).toHaveLength(2);
  });
});
