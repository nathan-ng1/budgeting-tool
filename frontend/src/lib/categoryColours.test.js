import { afterEach, describe, expect, it } from "vitest";

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

describe("colourForCategory under the Blossom theme", () => {
  afterEach(() => {
    delete document.documentElement.dataset.theme;
  });

  it("gives every known Expense Category its own colour, distinct from Terracotta's", () => {
    const terracottaColours = EXPENSE_CATEGORIES.map(colourForCategory);

    document.documentElement.dataset.theme = "blossom";
    const blossomColours = EXPENSE_CATEGORIES.map(colourForCategory);

    expect(new Set(blossomColours).size).toBe(EXPENSE_CATEGORIES.length);
    blossomColours.forEach((colour) => expect(colour).toMatch(/^#[0-9a-f]{6}$/i));
    // A Blossom-specific palette (Issue #102), not Terracotta's colours
    // relabelled - every slot differs, including the former green steps
    // (indices 4-7), which moved to a Blossom-only gold ramp after user
    // feedback that green read as off-theme against pink.
    expect(blossomColours).not.toEqual(terracottaColours);
  });

  it("keeps a Category in the same relative slot across themes", () => {
    // Same rank in each theme's palette, so switching themes doesn't also
    // reshuffle which Categories look alike or different from each other.
    document.documentElement.dataset.theme = "blossom";
    const groceriesBlossom = colourForCategory("Groceries");

    delete document.documentElement.dataset.theme;
    const groceriesTerracotta = colourForCategory("Groceries");

    document.documentElement.dataset.theme = "blossom";
    expect(colourForCategory("Groceries")).toBe(groceriesBlossom);
    expect(groceriesBlossom).not.toBe(groceriesTerracotta);
  });
});
