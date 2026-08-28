// The switcher shared by Overview, Budget, and Transactions (ADR-0021) offers
// two framings for "a year": a Financial Year (July 1 - June 30, named by the
// calendar year it starts in - see financialYear.js) or a Calendar Year
// (January 1 - December 31, named by the calendar year it is). This module
// generalises financialYear.js's pure logic to either framing via a
// caller-supplied start month, so the two read the same rather than existing
// as two parallel, subtly different implementations.

import { MONTH_LABELS_SHORT } from "./months.js";

export const PERIOD_TYPES = ["financial", "calendar"];

const START_MONTH = { financial: 7, calendar: 1 };

// A device-local display preference, not domain data (ADR-0008) - persisted
// the same way theme.js persists the colour theme.
const STORAGE_KEY = "dashboard.periodType";
const DEFAULT_PERIOD_TYPE = "financial";

export function startMonthFor(periodType) {
  return START_MONTH[periodType];
}

export function periodFor(year, month, periodType) {
  const startMonth = startMonthFor(periodType);
  return month >= startMonth ? year : year - 1;
}

export function monthsOfPeriod(referenceYear, periodType) {
  const startMonth = startMonthFor(periodType);
  return Array.from({ length: 12 }, (_, offset) => {
    const monthIndex = startMonth - 1 + offset;
    return {
      year: referenceYear + Math.floor(monthIndex / 12),
      month: (monthIndex % 12) + 1,
      label: MONTH_LABELS_SHORT[monthIndex % 12],
    };
  });
}

export function periodLabel(referenceYear, periodType) {
  return periodType === "calendar"
    ? `Calendar Year ${referenceYear}`
    : `${referenceYear}-${referenceYear + 1} Financial Year`;
}

// The Financial Year or Calendar Year containing `today` - the switcher's
// default on a fresh load, and the upper bound its Next arrow stops at
// (ADR-0021: the newest selectable year is whichever period contains today).
export function currentReferenceYear(periodType, today = new Date()) {
  return periodFor(today.getFullYear(), today.getMonth() + 1, periodType);
}

// The Financial Year or Calendar Year containing a bare "YYYY-MM-DD" date -
// e.g. the switcher's Previous arrow lower bound, which is whichever period
// contains the Transaction Log's earliest Transaction. Split rather than
// `new Date(isoDate)`, matching format.js's parts() - the latter reads a bare
// ISO date as midnight UTC, which is the wrong calendar date in any timezone
// behind UTC.
export function referenceYearContaining(isoDate, periodType) {
  const [year, month] = isoDate.split("-").map(Number);
  return periodFor(year, month, periodType);
}

// Where a `{ year, month }` selection (or Full year, as null) displays after
// a periodType flip. A specific month is an anchor to a real point in time,
// so flipping framing keeps it selected and only recomputes which
// referenceYear/label it's shown under (ADR-0021). Full year has no such
// anchor, so it falls back to the period containing today.
export function remapReferenceYear(selected, periodType, today = new Date()) {
  return selected === null
    ? currentReferenceYear(periodType, today)
    : periodFor(selected.year, selected.month, periodType);
}

export function getStoredPeriodType() {
  const stored = localStorage.getItem(STORAGE_KEY);
  return PERIOD_TYPES.includes(stored) ? stored : DEFAULT_PERIOD_TYPE;
}

export function storePeriodType(periodType) {
  localStorage.setItem(STORAGE_KEY, periodType);
}
