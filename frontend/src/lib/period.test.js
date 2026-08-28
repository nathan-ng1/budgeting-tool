import { afterEach, beforeEach, describe, expect, it } from "vitest";

import {
  currentMonth,
  currentReferenceYear,
  getStoredPeriodType,
  monthsOfPeriod,
  periodFor,
  periodLabel,
  referenceYearContaining,
  remapReferenceYear,
  storePeriodType,
} from "./period.js";

describe("periodFor", () => {
  it("puts July through December in the Financial Year that starts that calendar year", () => {
    expect(periodFor(2026, 7, "financial")).toBe(2026);
    expect(periodFor(2026, 12, "financial")).toBe(2026);
  });

  it("puts January through June in the Financial Year that started the previous calendar year", () => {
    expect(periodFor(2027, 1, "financial")).toBe(2026);
    expect(periodFor(2027, 6, "financial")).toBe(2026);
  });

  it("puts every month of a Calendar Year in the Calendar Year of the same number", () => {
    expect(periodFor(2026, 1, "calendar")).toBe(2026);
    expect(periodFor(2026, 12, "calendar")).toBe(2026);
  });
});

describe("monthsOfPeriod", () => {
  it("runs July to June for a Financial Year, carrying the calendar year over at the new year", () => {
    const months = monthsOfPeriod(2026, "financial");

    expect(months).toHaveLength(12);
    expect(months[0]).toEqual({ year: 2026, month: 7, label: "Jul" });
    expect(months[5]).toEqual({ year: 2026, month: 12, label: "Dec" });
    expect(months[6]).toEqual({ year: 2027, month: 1, label: "Jan" });
    expect(months[11]).toEqual({ year: 2027, month: 6, label: "Jun" });
  });

  it("runs January to December for a Calendar Year, never rolling the year over", () => {
    const months = monthsOfPeriod(2026, "calendar");

    expect(months).toHaveLength(12);
    expect(months[0]).toEqual({ year: 2026, month: 1, label: "Jan" });
    expect(months[11]).toEqual({ year: 2026, month: 12, label: "Dec" });
  });
});

describe("periodLabel", () => {
  it("spans the two calendar years a Financial Year covers", () => {
    expect(periodLabel(2026, "financial")).toBe("2026-2027 Financial Year");
  });

  it("names a Calendar Year by its one calendar year", () => {
    expect(periodLabel(2026, "calendar")).toBe("Calendar Year 2026");
  });
});

describe("currentReferenceYear", () => {
  it("names the Financial Year containing today", () => {
    expect(currentReferenceYear("financial", new Date(2026, 7, 21))).toBe(2026);
    expect(currentReferenceYear("financial", new Date(2027, 2, 1))).toBe(2026);
  });

  it("names the Calendar Year containing today", () => {
    expect(currentReferenceYear("calendar", new Date(2026, 7, 21))).toBe(2026);
  });
});

describe("currentMonth", () => {
  it("names today's real calendar month, regardless of periodType", () => {
    expect(currentMonth(new Date(2026, 7, 21))).toEqual({ year: 2026, month: 8 });
  });
});

describe("referenceYearContaining", () => {
  it("names the Financial Year containing a bare ISO date", () => {
    expect(referenceYearContaining("2025-12-17", "financial")).toBe(2025);
    expect(referenceYearContaining("2026-03-01", "financial")).toBe(2025);
  });

  it("names the Calendar Year containing a bare ISO date", () => {
    expect(referenceYearContaining("2025-12-17", "calendar")).toBe(2025);
  });
});

describe("remapReferenceYear", () => {
  it("keeps a selected month anchored to the same real month, recomputing its Financial Year", () => {
    // August 2026 is Calendar Year 2026, but Financial Year 2026 too (Jul-Jun).
    expect(remapReferenceYear({ year: 2026, month: 8 }, "financial")).toBe(2026);
  });

  it("keeps a selected month anchored to the same real month, recomputing its Calendar Year", () => {
    // February 2027 is Financial Year 2026 (Jul 2026-Jun 2027), but Calendar Year 2027.
    expect(remapReferenceYear({ year: 2027, month: 2 }, "calendar")).toBe(2027);
  });

  it("falls back to the period containing today when Full year (null) is selected", () => {
    expect(remapReferenceYear(null, "calendar", new Date(2026, 7, 21))).toBe(2026);
    expect(remapReferenceYear(null, "financial", new Date(2027, 2, 1))).toBe(2026);
  });
});

describe("periodType persistence", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("defaults to Financial Year when nothing is stored", () => {
    expect(getStoredPeriodType()).toBe("financial");
  });

  it("ignores a stored value that isn't a real periodType", () => {
    localStorage.setItem("dashboard.periodType", "fortnight");

    expect(getStoredPeriodType()).toBe("financial");
  });

  it("round-trips a stored periodType", () => {
    storePeriodType("calendar");

    expect(getStoredPeriodType()).toBe("calendar");
  });
});
