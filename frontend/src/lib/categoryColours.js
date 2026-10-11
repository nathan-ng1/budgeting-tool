// Rank-based Category colours. For each Overview period the Spending
// Categories (Expense and Bills & Subscriptions) are ranked by spend, largest
// first, and handed the active theme's palette slots in that order, wrapping
// around after the last slot. A Category's colour therefore follows its rank
// in the period, not its name: it can change from month to month (spec #177).
// 12 slots suffice - a wrapped Category repeats the colour of one ranked 12
// places above it, which is far down the long tail, and every card that draws
// a Category dot also prints its name beside the dot.
//
// The ramps are the mockup's "Organic" design-system tokens: the accent (warm)
// ramp, then the accent-2 (green) ramp, then neutrals.

import { getCurrentTheme } from "./theme.js";
import { TYPE_COLOURS } from "./typeColours.js";

const SPENDING_TYPES = ["Expense", "Bills & Subscriptions"];

// Income has no entry in TYPE_COLOURS (it is the axis of the allocation bar),
// but a Category dot on an Income row still needs a fill.
const INCOME_COLOUR = "var(--color-positive)";
const NEUTRAL_COLOUR = "var(--color-neutral-400)";

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
// categoryColours' callers), so none of these are held to the 4.5:1
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

// Builds the period's Category colour mapping once, from the Overview's
// spending_by_category rows, and returns `colourFor(category, type)`. Share the
// one function between every card that draws a Category dot so a Category is
// one colour across the page. A Spending Category with a rank gets its palette
// slot; any other Category (Income, Debt, Savings, or a Spending Category with
// no spend this period) gets its Type's colour.
export function categoryColours(spendingByCategory) {
  const palette = activePalette();
  const ranked = spendingByCategory
    .filter(({ type }) => SPENDING_TYPES.includes(type))
    .sort((a, b) => b.amount - a.amount || a.category.localeCompare(b.category));
  const slots = new Map(ranked.map(({ category }, rank) => [category, palette[rank % palette.length]]));

  return function colourFor(category, type) {
    return slots.get(category) ?? (type === "Income" ? INCOME_COLOUR : TYPE_COLOURS[type]) ?? NEUTRAL_COLOUR;
  };
}
