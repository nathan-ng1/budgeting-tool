import { describe, expect, it } from "vitest";

import { financialYearFor, financialYearLabel, monthsOfFinancialYear } from "./financialYear.js";

describe("financialYearFor", () => {
  it("puts July through December in the Financial Year that starts that calendar year", () => {
    expect(financialYearFor(2026, 7)).toBe(2026);
    expect(financialYearFor(2026, 12)).toBe(2026);
  });

  it("puts January through June in the Financial Year that started the previous calendar year", () => {
    expect(financialYearFor(2027, 1)).toBe(2026);
    expect(financialYearFor(2027, 6)).toBe(2026);
  });
});

describe("monthsOfFinancialYear", () => {
  it("runs July to June, carrying the calendar year over at the new year", () => {
    const months = monthsOfFinancialYear(2026);

    expect(months).toHaveLength(12);
    expect(months[0]).toEqual({ year: 2026, month: 7, label: "Jul" });
    expect(months[5]).toEqual({ year: 2026, month: 12, label: "Dec" });
    expect(months[6]).toEqual({ year: 2027, month: 1, label: "Jan" });
    expect(months[11]).toEqual({ year: 2027, month: 6, label: "Jun" });
  });
});

describe("financialYearLabel", () => {
  it("spans the two calendar years the Financial Year covers", () => {
    expect(financialYearLabel(2026)).toBe("2026-2027 Financial Year");
  });
});
