// Presentation-only formatting. Every number the Dashboard shows is already
// computed and rounded by the Month Overview endpoint (see Issue #27) - nothing
// here derives a new figure, it only decides how an existing one reads.

import { MONTH_LABELS_LONG, MONTH_LABELS_SHORT } from "./months.js";

// The mockup uses a typographic minus (U+2212) for signed figures - it lines up
// with the "+" at the same optical weight, which a hyphen doesn't.
const MINUS = "−";

function dollars(value) {
  return `$${Math.abs(Math.round(value)).toLocaleString("en-AU")}`;
}

export function money(value) {
  return Math.round(value) < 0 ? `-${dollars(value)}` : dollars(value);
}

export function signedMoney(value) {
  return `${Math.round(value) < 0 ? MINUS : "+"}${dollars(value)}`;
}

export function signedPct(value) {
  return `${Math.round(value) < 0 ? MINUS : "+"}${Math.abs(Math.round(value))}%`;
}

export function dayMonth(isoDate) {
  const { month, day } = parts(isoDate);
  return `${MONTH_LABELS_SHORT[month - 1]} ${day}`;
}

// The mockup's "As at" line spells the month out: "As at 19 August".
export function dayMonthLong(isoDate) {
  const { month, day } = parts(isoDate);
  return `${day} ${MONTH_LABELS_LONG[month - 1]}`;
}

function parts(isoDate) {
  // Split rather than `new Date(isoDate)`: the latter reads a bare ISO date as
  // midnight UTC, which renders as the previous day anywhere behind UTC.
  const [, month, day] = isoDate.split("-");
  return { month: Number(month), day: Number(day) };
}
