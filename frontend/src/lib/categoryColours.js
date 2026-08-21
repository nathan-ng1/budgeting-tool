// A fixed palette keyed by Category name, so a Category keeps the same colour
// in the donut, the legend, the Budgeted vs Actual dots and the Top 5 dots -
// and keeps it from month to month, where its rank by spend moves around.
//
// The ramps are the mockup's "Organic" design-system tokens: the accent (warm)
// ramp, then the accent-2 (green) ramp, then neutrals.
//
// This list mirrors the Expense Categories in src/transaction_log/categories.py
// (which holds them in a `set`, so it has no order of its own to follow - the
// order here is this file's own, and only decides which ramp step a Category
// gets). Adding a Category there without adding it here is not a breakage: it
// falls through to the hashed fallback below and still renders a stable colour,
// just not a hand-picked one.

export const EXPENSE_CATEGORIES = [
  "Groceries",
  "Dining & Takeaway",
  "Transport",
  "Shopping & Retail",
  "Holidays & Travel",
  "Entertainment & Leisure",
  "Health & Medical",
  "Donations & Giving",
  "Subscriptions",
  "Insurance & Bills",
  "Rental Expense",
  "Mortgage Repayment",
];

const PALETTE = [
  "#8c491a", // accent-700
  "#b2622d", // accent-600
  "#d67f48", // accent-500
  "#f6a06b", // accent-400
  "#56633f", // accent-2-700
  "#728157", // accent-2-600
  "#8fa073", // accent-2-500
  "#aebf92", // accent-2-400
  "#645c50", // neutral-700
  "#82796a", // neutral-600
  "#a19786", // neutral-500
  "#c0b6a5", // neutral-400
];

const ASSIGNED = new Map(EXPENSE_CATEGORIES.map((category, index) => [category, PALETTE[index % PALETTE.length]]));

export function colourForCategory(category) {
  const assigned = ASSIGNED.get(category);
  if (assigned !== undefined) {
    return assigned;
  }

  // An unrecognised Category still needs a colour that is stable across
  // renders, so derive one from the name rather than from render order.
  let hash = 0;
  for (let i = 0; i < category.length; i += 1) {
    hash = (hash * 31 + category.charCodeAt(i)) % 1000003;
  }
  return PALETTE[hash % PALETTE.length];
}
