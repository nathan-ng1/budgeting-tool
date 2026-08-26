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

// Orchid's own palette (Issue #102 follow-up #2, replacing Blossom's):
// a Category keeps the same *slot* (index) as under Terracotta, so
// switching themes doesn't reshuffle which Categories look alike or
// different from each other - just what they look like. Four shades each of
// the accent (pink), positive (lavender) and neutral (taupe) hues from the
// theme's source palette - settled via /grilling then /prototype (see
// prototype/orchid-theme-palette). Indices 4-7 were Blossom's gold ramp
// before that; lavender replaces it since positive/Income share that hue
// under Orchid, and gold doesn't exist in Orchid's palette at all.
// PROTOTYPE (prototype/orchid-theme-variants): slots 4-11 (previously a
// lavender ramp tied to the old purple --color-positive, then a taupe ramp
// tied to the old brown neutral ramp) are under an A/B/C comparison
// alongside the CSS token variants in styles.css - see
// [data-orchid-variant] there. Slots 0-3 (pink/accent) are unchanged and
// not part of the comparison. Real code keeps only the winning array.
const ORCHID_PALETTE_PINK = ["#71285d", "#9f3883", "#c355a6", "#d586bf"];
const ORCHID_PALETTE_VARIANTS = {
  A: ["#b0d09f", "#88b86f", "#689d4d", "#4d7439", "#7a5270", "#a37597", "#be9db5", "#d6c2d1"],
  B: ["#add897", "#83c563", "#63ab3f", "#497f2f", "#874575", "#b1689d", "#c893ba", "#dcbcd4"],
  C: ["#b2c7a8", "#8cab7c", "#6d8f5b", "#506a44", "#725a6c", "#9a7e93", "#b7a4b2", "#d2c6cf"],
};

function orchidPalette() {
  const variant = document.documentElement.dataset.orchidVariant;
  const rest = ORCHID_PALETTE_VARIANTS[variant] ?? ORCHID_PALETTE_VARIANTS.A;
  return [...ORCHID_PALETTE_PINK, ...rest];
}

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
  midnight: MIDNIGHT_PALETTE,
};

function activePalette() {
  const theme = getCurrentTheme();
  if (theme === "orchid") {
    return orchidPalette();
  }
  return THEME_PALETTES[theme] ?? PALETTE;
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
