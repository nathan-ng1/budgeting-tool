import { describe, expect, it } from "vitest";

import { EXPENSE_CATEGORIES, colourForCategory } from "./categoryColours.js";

describe("colourForCategory", () => {
  it("gives every known Expense Category its own colour", () => {
    const colours = EXPENSE_CATEGORIES.map(colourForCategory);

    expect(new Set(colours).size).toBe(EXPENSE_CATEGORIES.length);
    colours.forEach((colour) => expect(colour).toMatch(/^#[0-9a-f]{6}$/i));
  });

  it("keys the colour to the Category name, not to its rank in a list", () => {
    // The same Category has to keep its colour across the donut, the legend,
    // the Budgeted vs Actual dots and the Top 5 dots - and across months, where
    // its rank by spend changes.
    const groceries = colourForCategory("Groceries");

    expect(colourForCategory("Groceries")).toBe(groceries);
    expect(colourForCategory("Transport")).not.toBe(groceries);
  });

  it("gives an unknown Category a stable colour rather than undefined", () => {
    // Categories are added lazily as real cases occur (CONTEXT.md), so the
    // frontend must not break on one it was not built with.
    const first = colourForCategory("Some Future Category");

    expect(first).toMatch(/^#[0-9a-f]{6}$/i);
    expect(colourForCategory("Some Future Category")).toBe(first);
  });
});
