import { describe, expect, it } from "vitest";

import { categoryLabel, emojiLookup } from "./categories.js";

function category(overrides = {}) {
  return { id: 1, type: "Expense", name: "Groceries", emoji: null, locked: false, ...overrides };
}

describe("emojiLookup / categoryLabel", () => {
  it("labels a Category with its emoji when one is set", () => {
    const emoji = emojiLookup([category({ name: "Groceries", emoji: "🛒" })]);

    expect(categoryLabel("Groceries", emoji)).toBe("🛒 Groceries");
  });

  it("labels a Category with just its name when it has no emoji", () => {
    const emoji = emojiLookup([category({ name: "Groceries", emoji: null })]);

    expect(categoryLabel("Groceries", emoji)).toBe("Groceries");
  });

  it("labels an unrecognised Category name with just the name, not an error", () => {
    const emoji = emojiLookup([category({ name: "Groceries", emoji: "🛒" })]);

    expect(categoryLabel("Some Future Category", emoji)).toBe("Some Future Category");
  });

  it("degrades to name-only labels when the Categories list hasn't loaded yet", () => {
    const emoji = emojiLookup(undefined);

    expect(categoryLabel("Groceries", emoji)).toBe("Groceries");
  });
});
