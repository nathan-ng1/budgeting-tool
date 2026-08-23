import { describe, expect, it } from "vitest";

import { changesFrom, valuesFrom } from "./budgetEditorForm.js";

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
