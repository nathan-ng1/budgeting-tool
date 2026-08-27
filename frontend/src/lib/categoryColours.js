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
// look like.
//
// Re-derived wholesale in pass 9 (prototype/orchid-pastel-palette) at the
// user's request to "match the new ramping between hot pink and royal
// purple" - the CSS side's --color-negative-fill (hot pink, H=330) and
// --color-positive/--color-accent-2-500 (royal purple, H=278) waypoints.
// This replaces the three-separate-family arrangement passes 6-8 left
// behind (a pink family at 0-3, a purple family at 4-7 re-hued twice
// chasing --color-positive, and a leftover neutral/mauve family at 8-11
// tied to the old neutral ramp) with one continuous sweep: three 4-shade
// bands at H=330 (hot pink) -> H=304 (midpoint) -> H=278 (royal purple),
// each band running dark-to-light (S=65%, L=26/42/58/74 - the same >=16%
// per-step lightness delta pass 6 established for telling adjacent chart
// segments apart). All fill-only (donut segments, legend/list dots - see
// colourForCategory's callers), so none of these are held to the 4.5:1
// text bar. Band 3's second step (index 9, H=278/L=42) lands on
// #7e25b1 - the exact same value as --color-accent-2-500 - confirming the
// derivation lines up with the CSS tokens it's ramping between, not a
// deliberate cross-reference.
const ORCHID_PALETTE = [
  "#6d1742",
  "#b1256b",
  "#d94e94",
  "#e892bd",
  "#6d1768",
  "#b125a7",
  "#d94ed0",
  "#e892e2",
  "#4e176d",
  "#7e25b1",
  "#a64ed9",
  "#c892e8",
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
