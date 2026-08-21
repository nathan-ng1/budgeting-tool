// Which way a figure went, as a CSS class. Overspending and a negative Net
// Balance are adverse; staying under a Category Budget and a positive Net
// Balance are favourable. Exactly zero is neither, so it stays unstyled.

export const ADVERSE = "figure--adverse";
export const FAVOURABLE = "figure--favourable";

export function toneFor(value) {
  if (value === 0) {
    return "";
  }
  return value > 0 ? ADVERSE : FAVOURABLE;
}
