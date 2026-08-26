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

import { getCurrentTheme } from "./theme.js";

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

// Slots 4-7 (the accent-2/green ramp) were re-derived in Issue #111
// alongside --color-positive's move off a hand-picked literal onto a
// documented hue formula (~88deg, see styles.css's :root comment) - settled
// via /prototype (see prototype/terracotta-theme-variants; Variant C,
// "Muted" won). Slots 0-3 (accent) and 8-11 (neutral) are unchanged. As
// before this revision, every slot with a same-named CSS custom property
// (700/600 in the accent ramp, 700/500 in the accent-2 ramp, every step in
// the neutral ramp) stays byte-identical to that property's value - slots
// 5/7 (accent-2-600/400) have no CSS-token counterpart, so are this file's
// own interpolated in-between steps.
const PALETTE = [
  "#8c491a", // accent-700 == --color-accent-700
  "#b2622d", // accent-600 == --color-accent-600
  "#d67f48", // accent-500 (no CSS token - interpolated)
  "#f6a06b", // accent-400 (no CSS token - interpolated)
  "#53653e", // accent-2-700 == --color-positive
  "#697e52", // accent-2-600 (no CSS token - interpolated)
  "#95a583", // accent-2-500 == --color-accent-2-500
  "#c1c7ba", // accent-2-400 (no CSS token - interpolated)
  "#645c50", // neutral-700 == --color-neutral-700
  "#82796a", // neutral-600 == --color-neutral-600
  "#a19786", // neutral-500 == --color-neutral-500
  "#c0b6a5", // neutral-400 == --color-neutral-400
];

// Orchid's own palette: a Category keeps the same *slot* (index) as under
// every other theme, so switching themes doesn't reshuffle which
// Categories look alike or different from each other - just what they
// look like. Four shades each of the accent (pink), positive (sage green)
// and neutral (mauve/rose-grey) hues.
//
// Indices 4-7 and 8-11 were revised in Issue #108 (a lavender ramp tied to
// the old purple --color-positive, and a taupe ramp tied to the old brown
// neutral ramp, respectively) to follow those tokens' new hues - settled
// via /grilling then /prototype (see prototype/orchid-theme-variants;
// "Variant B, Richer" won a three-variant comparison). Indices 0-3 are
// unchanged since Issue #102 follow-up #2 (see prototype/orchid-theme-palette).
const ORCHID_PALETTE = [
  "#71285d",
  "#9f3883",
  "#c355a6",
  "#d586bf",
  "#add897",
  "#83c563",
  "#63ab3f",
  "#497f2f",
  "#874575",
  "#b1689d",
  "#c893ba",
  "#dcbcd4",
];

// Midnight's own palette (Issue #106): same slot-per-Category convention as
// Orchid. Four shades each of the accent (blue), positive (amber -
// Midnight's one new hue, since its source palette is monochrome blue) and
// neutral (desaturated blue) hues - settled via /grilling then /prototype
// (see prototype/midnight-theme-variants; "Option C - Muted" won the
// three-variant comparison).
const MIDNIGHT_PALETTE = [
  "#2e719e",
  "#4192c8",
  "#71add6",
  "#a0c8e3",
  "#ab852b",
  "#d0a643",
  "#dcbd74",
  "#e9d4a5",
  "#465d6d",
  "#5f8095",
  "#839daf",
  "#a8bbc7",
];

const THEME_PALETTES = {
  orchid: ORCHID_PALETTE,
  midnight: MIDNIGHT_PALETTE,
};

function activePalette() {
  return THEME_PALETTES[getCurrentTheme()] ?? PALETTE;
}

export function colourForCategory(category) {
  const palette = activePalette();
  const index = EXPENSE_CATEGORIES.indexOf(category);
  if (index !== -1) {
    return palette[index % palette.length];
  }

  // An unrecognised Category still needs a colour that is stable across
  // renders, so derive one from the name rather than from render order.
  let hash = 0;
  for (let i = 0; i < category.length; i += 1) {
    hash = (hash * 31 + category.charCodeAt(i)) % 1000003;
  }
  return palette[hash % palette.length];
}
