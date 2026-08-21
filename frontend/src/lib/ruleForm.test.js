import { describe, expect, it } from "vitest";

import { blankValues, toPayload, valuesFrom, weekdayOf, withFrequency, withStartDate, withType } from "./ruleForm.js";

const CATEGORIES = { Expense: ["Subscriptions", "Groceries"], Income: ["Salary"] };

describe("weekdayOf", () => {
  it("names the weekday a date falls on", () => {
    expect(weekdayOf("2026-08-05")).toBe("Wednesday");
  });

  it("reads the date as local, so it doesn't slip a day behind UTC", () => {
    expect(weekdayOf("2026-08-09")).toBe("Sunday");
  });
});

describe("withStartDate", () => {
  it("keeps a Weekly rule's Day on whatever weekday it now starts", () => {
    const values = withStartDate({ ...blankValues(), frequency: "Weekly" }, "2026-08-05");

    expect(values.day).toBe("Wednesday");
  });

  it("keeps a Monthly rule's Day on whatever day-of-month it now starts", () => {
    const values = withStartDate({ ...blankValues(), frequency: "Monthly" }, "2026-01-15");

    expect(values.day).toBe(15);
  });

  it("keeps a deliberate Day 31 when the new Start Date still clamps to it", () => {
    // Day 31 starting 28 Feb is legitimate - it clamps to the month's last day.
    // Moving the start to 30 April still clamps to Day 31, so the rule must
    // keep meaning "the 31st", not quietly become a Day 30 rule.
    const shortMonth = { ...blankValues(), frequency: "Monthly", day: 31, start_date: "2026-02-28" };

    expect(withStartDate(shortMonth, "2026-04-30").day).toBe(31);
  });

  it("re-derives Day when the new Start Date can no longer mean the old one", () => {
    const shortMonth = { ...blankValues(), frequency: "Monthly", day: 31, start_date: "2026-02-28" };

    expect(withStartDate(shortMonth, "2026-03-15").day).toBe(15);
  });
});

describe("withFrequency", () => {
  it("re-derives Day when a rule switches from Weekly to Monthly", () => {
    const weekly = withStartDate({ ...blankValues(), frequency: "Weekly" }, "2026-01-15");

    const monthly = withFrequency(weekly, "Monthly");

    expect(monthly.frequency).toBe("Monthly");
    expect(monthly.day).toBe(15);
  });

  it("re-derives Day when a rule switches from Monthly to Weekly", () => {
    const monthly = withStartDate({ ...blankValues(), frequency: "Monthly" }, "2026-08-05");

    expect(withFrequency(monthly, "Weekly").day).toBe("Wednesday");
  });
});

describe("withType", () => {
  it("moves the Category to one the new Type actually allows", () => {
    const values = { ...blankValues(), type: "Expense", category: "Subscriptions" };

    expect(withType(values, "Income", CATEGORIES).category).toBe("Salary");
  });

  it("leaves the Category alone when it is already valid for the Type", () => {
    const values = { ...blankValues(), type: "Expense", category: "Groceries" };

    expect(withType(values, "Expense", CATEGORIES).category).toBe("Groceries");
  });
});

describe("valuesFrom / toPayload", () => {
  it("round-trips a rule through the form without changing it", () => {
    const rule = {
      id: 3,
      amount: 100,
      type: "Expense",
      category: "Subscriptions",
      notes: "Streaming service",
      frequency: "Weekly",
      interval: 2,
      day: "Wednesday",
      start_date: "2026-08-05",
      end_date: "2026-12-31",
    };

    const { id, ...withoutId } = rule;
    expect(toPayload(valuesFrom(rule))).toEqual(withoutId);
  });

  it("sends a blank End Date as null, since that means recurs indefinitely", () => {
    expect(toPayload({ ...blankValues(), end_date: "" }).end_date).toBeNull();
  });

  it("sends Amount and Interval as numbers, not the strings the inputs hold", () => {
    const payload = toPayload({ ...blankValues(), amount: "100.50", interval: "2" });

    expect(payload.amount).toBe(100.5);
    expect(payload.interval).toBe(2);
  });
});
