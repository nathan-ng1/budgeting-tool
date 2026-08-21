// The Overview tab is organised around the Financial Year — July 1 to June 30
// (see CONTEXT.md). A Financial Year is named by the calendar year it starts
// in, so "Financial Year 2026" runs July 2026 through June 2027.

import { MONTH_LABELS_SHORT } from "./months.js";

export const FINANCIAL_YEAR_START_MONTH = 7;

export function financialYearFor(year, month) {
  return month >= FINANCIAL_YEAR_START_MONTH ? year : year - 1;
}

export function monthsOfFinancialYear(financialYear) {
  return Array.from({ length: 12 }, (_, offset) => {
    const monthIndex = FINANCIAL_YEAR_START_MONTH - 1 + offset;
    return {
      year: financialYear + Math.floor(monthIndex / 12),
      month: (monthIndex % 12) + 1,
      label: MONTH_LABELS_SHORT[monthIndex % 12],
    };
  });
}

export function financialYearLabel(financialYear) {
  return `${financialYear}-${financialYear + 1} Financial Year`;
}
