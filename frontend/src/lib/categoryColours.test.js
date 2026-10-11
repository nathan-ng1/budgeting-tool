import { afterEach, describe, expect, it } from "vitest";

import { categoryColours } from "./categoryColours.js";
import { TYPE_COLOURS } from "./typeColours.js";

const HEX = /^#[0-9a-f]{6}$/i;

// Slot literals of each theme's palette (the first two slots, then the last).
const THEMES = {
  terracotta: { first: "#8c491a", second: "#b2622d", last: "#c0b6a5" },
  orchid: { first: "#6d1742", second: "#b1256b", last: "#c892e8" },
  midnight: { first: "#2e719e", second: "#4192c8", last: "#a8bbc7" },
};

function spendingRows(...names) {
  // Listed in descending spend: the first name is the biggest.
  return names.map((category, index) => ({
    category,
    type: "Expense",
    amount: 1000 - index * 10,
  }));
}

function selectTheme(theme) {
  if (theme === "terracotta") {
    delete document.documentElement.dataset.theme;
  } else {
    document.documentElement.dataset.theme = theme;
  }
}

describe.each(Object.entries(THEMES))("categoryColours under the %s theme", (theme, slots) => {
  afterEach(() => {
    delete document.documentElement.dataset.theme;
  });

  it("gives the largest-spend Category the first slot and follows spend downwards", () => {
    selectTheme(theme);
    const colourFor = categoryColours([
      { category: "Transport", type: "Expense", amount: 200 },
      { category: "Groceries", type: "Expense", amount: 900 },
    ]);

    expect(colourFor("Groceries", "Expense")).toBe(slots.first);
    expect(colourFor("Transport", "Expense")).toBe(slots.second);
  });

  it("wraps around to the first slot after the last", () => {
    selectTheme(theme);
    const names = Array.from({ length: 13 }, (_, i) => `Category ${String(i).padStart(2, "0")}`);
    const colourFor = categoryColours(spendingRows(...names));

    expect(colourFor(names[11], "Expense")).toBe(slots.last);
    expect(colourFor(names[12], "Expense")).toBe(slots.first);
    names.slice(0, 12).forEach((name) => expect(colourFor(name, "Expense")).toMatch(HEX));
    expect(new Set(names.slice(0, 12).map((name) => colourFor(name, "Expense"))).size).toBe(12);
  });
});

describe("categoryColours", () => {
  it("breaks a spend tie by Category name", () => {
    const colourFor = categoryColours([
      { category: "Zoo", type: "Expense", amount: 100 },
      { category: "Aquarium", type: "Expense", amount: 100 },
    ]);

    expect(colourFor("Aquarium", "Expense")).toBe(THEMES.terracotta.first);
    expect(colourFor("Zoo", "Expense")).toBe(THEMES.terracotta.second);
  });

  it("ranks Expense and Bills & Subscriptions Categories together as Spending", () => {
    const colourFor = categoryColours([
      { category: "Groceries", type: "Expense", amount: 300 },
      { category: "Internet", type: "Bills & Subscriptions", amount: 500 },
    ]);

    expect(colourFor("Internet", "Bills & Subscriptions")).toBe(THEMES.terracotta.first);
    expect(colourFor("Groceries", "Expense")).toBe(THEMES.terracotta.second);
  });

  it("does not let a Category outside Spending take a slot", () => {
    const colourFor = categoryColours([
      { category: "Groceries", type: "Expense", amount: 300 },
      { category: "Mortgage", type: "Debt", amount: 2000 },
    ]);

    expect(colourFor("Groceries", "Expense")).toBe(THEMES.terracotta.first);
  });

  it("gives a Category outside Spending its Type's colour", () => {
    const colourFor = categoryColours(spendingRows("Groceries"));

    expect(colourFor("Mortgage", "Debt")).toBe(TYPE_COLOURS.Debt);
    expect(colourFor("Emergency Fund", "Savings")).toBe(TYPE_COLOURS.Savings);
    expect(colourFor("Salary", "Income")).toMatch(/^var\(--/);
  });

  it("gives a Spending Category with no spend this period its Type's colour", () => {
    const colourFor = categoryColours(spendingRows("Groceries"));

    expect(colourFor("Dining & Takeaway", "Expense")).toBe(TYPE_COLOURS.Expense);
  });

  it("gives an unrecognised Category with no Type a neutral colour rather than undefined", () => {
    const colourFor = categoryColours([]);

    expect(colourFor("Whatever")).toMatch(/^var\(--/);
  });

  it("reads the palette of the theme active when the mapping is built", () => {
    const rows = spendingRows("Groceries");
    const terracotta = categoryColours(rows)("Groceries", "Expense");

    document.documentElement.dataset.theme = "orchid";
    const orchid = categoryColours(rows)("Groceries", "Expense");
    delete document.documentElement.dataset.theme;

    expect(orchid).not.toBe(terracotta);
  });
});
