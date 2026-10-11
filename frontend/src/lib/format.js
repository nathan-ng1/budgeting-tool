// Presentation-only formatting. Every number the Dashboard shows is already
// computed and rounded by the Month Overview endpoint (see Issue #27) - nothing
// here derives a new figure, it only decides how an existing one reads.

import { DEFAULT_CURRENCY_ID, currencyEntry } from "./currencies.js";
import { MONTH_LABELS_LONG, MONTH_LABELS_SHORT } from "./months.js";

// The mockup uses a typographic minus (U+2212) for signed figures - it lines up
// with the "+" at the same optical weight, which a hyphen doesn't.
const MINUS = "−";

// How an unset figure (a Category Budget never set, a historical column with
// insufficient data) renders - shared so it reads the same everywhere rather
// than each component picking its own dash.
export const UNSET = "—";

// Every amount is formatted by the browser's Intl.NumberFormat, driven by the
// chosen Display Currency entry (see currencies.js): its symbol, symbol
// position and separators. Display only - the number is never converted.
// `currency` is the entry's id; an unknown one reads as the default.
const formatters = new Map();

function formatter(currencyId, roundedToUnits) {
  const key = `${currencyId}|${roundedToUnits}`;
  if (!formatters.has(key)) {
    const { code, locale } = currencyEntry(currencyId);
    const rounding = roundedToUnits ? { minimumFractionDigits: 0, maximumFractionDigits: 0 } : {};
    formatters.set(key, new Intl.NumberFormat(locale, { style: "currency", currency: code, ...rounding }));
  }
  return formatters.get(key);
}

// Whole units, sign left to the caller so money() and signedMoney() share it.
function wholeUnits(value, currency) {
  return formatter(currency, true).format(Math.abs(Math.round(value)));
}

export function money(value, currency = DEFAULT_CURRENCY_ID) {
  return Math.round(value) < 0 ? `-${wholeUnits(value, currency)}` : wholeUnits(value, currency);
}

// The currency's own decimals (two for most, none for yen), unlike money()
// above - for editable/raw figures (a Recurring Rule's Amount, a
// Transaction's Amount) rather than the Overview's rounded summaries.
export function preciseMoney(value, currency = DEFAULT_CURRENCY_ID) {
  return formatter(currency, false).format(Number(value));
}

export function signedMoney(value, currency = DEFAULT_CURRENCY_ID) {
  return `${Math.round(value) < 0 ? MINUS : "+"}${wholeUnits(value, currency)}`;
}

export function signedPct(value) {
  return `${Math.round(value) < 0 ? MINUS : "+"}${Math.abs(Math.round(value))}%`;
}

export function pct(value) {
  return `${Math.round(value)}%`;
}

// Date Order (ADR-0027): "day-first" writes "19 Aug", "month-first" writes
// "Aug 19". Month names always come from the English month labels. An
// unset or unknown order reads day-first, the default.
export const DEFAULT_DATE_ORDER = "day-first";

function dayAndMonth(day, monthName, order) {
  return order === "month-first" ? `${monthName} ${day}` : `${day} ${monthName}`;
}

export function dayMonth(isoDate, order = DEFAULT_DATE_ORDER) {
  const { month, day } = parts(isoDate);
  return dayAndMonth(day, MONTH_LABELS_SHORT[month - 1], order);
}

// The mockup's "As at" line spells the month out: "As at 19 August".
export function dayMonthLong(isoDate, order = DEFAULT_DATE_ORDER) {
  const { month, day } = parts(isoDate);
  return dayAndMonth(day, MONTH_LABELS_LONG[month - 1], order);
}

// Unlike dayMonth/dayMonthLong above, this is a real instant (the Budget
// Suggestion's generated_at), so `new Date()` is the correct way to read it,
// not the plain-calendar-date pitfall those two avoid.
export function generatedAt(isoDateTime, order = DEFAULT_DATE_ORDER) {
  const date = new Date(isoDateTime);
  const hours = date.getHours();
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const period = hours < 12 ? "am" : "pm";
  const hour12 = ((hours + 11) % 12) + 1;
  const dayMonthPart = dayAndMonth(date.getDate(), MONTH_LABELS_SHORT[date.getMonth()], order);
  const datePart = order === "month-first" ? `${dayMonthPart}, ${date.getFullYear()}` : `${dayMonthPart} ${date.getFullYear()}`;
  return `${datePart}, ${hour12}:${minutes}${period}`;
}

function parts(isoDate) {
  // Split rather than `new Date(isoDate)`: the latter reads a bare ISO date as
  // midnight UTC, which renders as the previous day anywhere behind UTC.
  const [, month, day] = isoDate.split("-");
  return { month: Number(month), day: Number(day) };
}
