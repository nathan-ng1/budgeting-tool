import { describe, expect, it } from "vitest";

import { dayMonth, dayMonthLong, generatedAt, money, pct, signedMoney, signedPct } from "./format.js";

describe("money", () => {
  it("renders whole dollars with a thousands separator", () => {
    expect(money(5240)).toBe("$5,240");
    expect(money(0)).toBe("$0");
  });

  it("rounds to the nearest dollar - cents are noise at this altitude", () => {
    expect(money(3666.51)).toBe("$3,667");
  });

  it("renders a negative amount with the sign outside the dollar sign", () => {
    expect(money(-42)).toBe("-$42");
  });
});

describe("signedMoney", () => {
  it("always carries an explicit sign, using a real minus glyph", () => {
    expect(signedMoney(40)).toBe("+$40");
    expect(signedMoney(-38)).toBe("−$38");
    expect(signedMoney(0)).toBe("+$0");
  });
});

describe("signedPct", () => {
  it("always carries an explicit sign and a rounded whole percent", () => {
    expect(signedPct(2.2)).toBe("+2%");
    expect(signedPct(-6.1)).toBe("−6%");
  });
});

describe("pct", () => {
  it("renders a rounded whole percent, with no sign", () => {
    expect(pct(76.2)).toBe("76%");
    expect(pct(0)).toBe("0%");
  });
});

describe("dayMonth", () => {
  it("renders an ISO date the way the Top 5 list shows it", () => {
    expect(dayMonth("2026-05-01")).toBe("May 1");
    expect(dayMonth("2026-05-30")).toBe("May 30");
  });

  it("reads the ISO date as a plain calendar date, not a UTC instant", () => {
    // Parsing "2026-05-01" via `new Date()` yields midnight UTC, which is the
    // previous day in any behind-UTC timezone - the date must not shift.
    expect(dayMonth("2026-01-01")).toBe("Jan 1");
  });
});

describe("dayMonthLong", () => {
  it("spells the month out, the way the mockup's 'As at' line reads", () => {
    expect(dayMonthLong("2026-08-19")).toBe("19 August");
  });
});

describe("generatedAt", () => {
  it("renders a full timestamp with a 12-hour clock", () => {
    expect(generatedAt("2026-08-20T14:32:00")).toBe("20 Aug 2026, 2:32pm");
  });

  it("renders midnight and noon as 12, not 0", () => {
    expect(generatedAt("2026-08-20T00:05:00")).toBe("20 Aug 2026, 12:05am");
    expect(generatedAt("2026-08-20T12:00:00")).toBe("20 Aug 2026, 12:00pm");
  });
});
