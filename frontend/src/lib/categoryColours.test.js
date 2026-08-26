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

describe("colourForCategory under the Orchid theme", () => {
  afterEach(() => {
    delete document.documentElement.dataset.theme;
  });

  it("gives every known Expense Category its own colour, distinct from Terracotta's", () => {
    const terracottaColours = EXPENSE_CATEGORIES.map(colourForCategory);

    document.documentElement.dataset.theme = "orchid";
    const orchidColours = EXPENSE_CATEGORIES.map(colourForCategory);

    expect(new Set(orchidColours).size).toBe(EXPENSE_CATEGORIES.length);
    orchidColours.forEach((colour) => expect(colour).toMatch(/^#[0-9a-f]{6}$/i));
    // An Orchid-specific palette (Issue #102 follow-up #2), not Terracotta's
    // colours relabelled - every slot differs, including indices 4-7, which
    // moved from Blossom's gold ramp to a lavender ramp (Orchid's positive/
    // Income hue - gold doesn't exist in Orchid's source palette).
    expect(orchidColours).not.toEqual(terracottaColours);
  });

  it("keeps a Category in the same relative slot across themes", () => {
    // Same rank in each theme's palette, so switching themes doesn't also
    // reshuffle which Categories look alike or different from each other.
    document.documentElement.dataset.theme = "orchid";
    const groceriesOrchid = colourForCategory("Groceries");

    delete document.documentElement.dataset.theme;
    const groceriesTerracotta = colourForCategory("Groceries");

    document.documentElement.dataset.theme = "orchid";
    expect(colourForCategory("Groceries")).toBe(groceriesOrchid);
    expect(groceriesOrchid).not.toBe(groceriesTerracotta);
  });
});
