// Shared support for /api/categories's flat Category list (Issue #91) - every
// consumer that still needs Category names grouped by Type (the Transaction
// and Recurring Rule forms' Type/Category selects) derives that view from
// here, so the grouping logic exists in exactly one place.

// CONTEXT.md's own Type order, not alphabetical - so a Type select built from
// this matches the Types filter dropdown's order.
export const TYPE_ORDER = ["Income", "Expense", "Debt", "Savings"];

// A curated quick-pick set for Category Management's emoji picker (Issue
// #91) - free text still works alongside it, this is just a shortcut for
// common choices.
export const EMOJI_PICKS = [
  "🛒", "🍔", "🚗", "🛍️", "✈️", "🎬", "🏥", "❤️", "📺", "🧾", "🏠", "💰",
  "🏦", "💳", "📈", "🎁", "⚡", "📱", "🐾", "☕", "🔄", "🎓", "🧘", "🐶",
];

export function groupByType(categories) {
  const names = {};
  for (const category of categories) {
    (names[category.type] ??= []).push(category.name);
  }

  const result = {};
  for (const type of TYPE_ORDER) {
    // A Type with no Categories yet is omitted - offering it would let a
    // form build a rule/transaction the store then rejects.
    if (names[type]?.length) {
      result[type] = [...names[type]].sort();
    }
  }
  return result;
}

// Category name -> emoji (Issue #92) - the one lookup every display site
// joins against, built from the same flat /api/categories list groupByType
// reads. `categories` defaults to empty so a tab that hasn't finished
// loading them yet (or whose fetch failed) degrades to name-only labels
// rather than throwing.
export function emojiLookup(categories) {
  const map = new Map();
  if (!Array.isArray(categories)) {
    return map;
  }
  for (const category of categories) {
    if (category.emoji) {
      map.set(category.name, category.emoji);
    }
  }
  return map;
}

// A Category's display label: "emoji name" once it has one, name-only
// otherwise - including for a name the lookup doesn't recognise at all,
// which is never an error here (a stale/renamed Category should still
// render, just without an emoji).
export function categoryLabel(name, emoji) {
  const found = emoji.get(name);
  return found ? `${found} ${name}` : name;
}
