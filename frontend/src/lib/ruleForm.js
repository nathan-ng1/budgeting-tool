// Form state for one Recurring Transactions Config rule (Issue #29).
//
// A rule's Day has to agree with its Start Date - a Weekly rule starting on a
// Wednesday must say "Wednesday", and a Monthly one starting on the 15th must
// say 15 - so the store rejects a pair that disagrees. Rather than let the
// form build that rule and report the error afterwards, Day is derived from
// Start Date here and never entered independently for Weekly rules.

// Monday-first, matching recurring/rules.py's WEEKDAY_NAMES.
export const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export const FREQUENCIES = ["Weekly", "Monthly"];

export function weekdayOf(isoDate) {
  const { year, month, day } = parts(isoDate);
  // Local midnight, not `new Date(isoDate)` - the latter reads a bare ISO date
  // as UTC, which lands on the previous day anywhere behind it.
  const weekday = new Date(year, month - 1, day).getDay();
  // JS counts from Sunday; WEEKDAYS counts from Monday.
  return WEEKDAYS[(weekday + 6) % 7];
}

export function dayOfMonthOf(isoDate) {
  return parts(isoDate).day;
}

export function blankValues(startDate = today()) {
  return withStartDate(
    {
      amount: "",
      type: "Expense",
      category: "",
      notes: "",
      frequency: "Weekly",
      interval: 1,
      day: "",
      start_date: startDate,
      end_date: "",
    },
    startDate,
  );
}

export function valuesFrom(rule) {
  return {
    amount: String(rule.amount),
    type: rule.type,
    category: rule.category,
    notes: rule.notes,
    frequency: rule.frequency,
    interval: rule.interval,
    day: rule.day,
    start_date: rule.start_date,
    end_date: rule.end_date ?? "",
  };
}

export function withStartDate(values, startDate) {
  return { ...values, start_date: startDate, day: dayFor(values.frequency, startDate, values.day) };
}

export function withFrequency(values, frequency) {
  // Switching Frequency reinterprets Day entirely (a weekday name is not a
  // day-of-month), so the old value can't be carried across.
  return { ...values, frequency, day: dayFor(frequency, values.start_date) };
}

export function withType(values, type, categoriesByType) {
  const allowed = categoriesByType[type] ?? [];
  // A Category belongs to exactly one Type (ADR-0006), so changing Type
  // always invalidates the Category unless the form is being rebuilt.
  return {
    ...values,
    type,
    category: allowed.includes(values.category) ? values.category : (allowed[0] ?? ""),
  };
}

export function toPayload(values) {
  return {
    amount: Number(values.amount),
    type: values.type,
    category: values.category,
    notes: values.notes,
    frequency: values.frequency,
    interval: Number(values.interval),
    day: values.day,
    start_date: values.start_date,
    // Blank means recurs indefinitely (CONTEXT.md), which the store stores as
    // no End Date at all rather than as an empty string.
    end_date: values.end_date === "" ? null : values.end_date,
  };
}

function dayFor(frequency, startDate, currentDay) {
  if (!startDate) {
    return "";
  }
  if (frequency === "Weekly") {
    return weekdayOf(startDate);
  }
  // A Monthly Day the user set on purpose can be past the start month's end -
  // Day 31 starting 28 Feb clamps to the last day. Keep such a Day whenever the
  // new Start Date still clamps to it, so moving 28 Feb to 30 Apr doesn't
  // quietly demote a "the 31st" rule to a "the 30th" one.
  if (clampsTo(currentDay, startDate)) {
    return currentDay;
  }
  return dayOfMonthOf(startDate);
}

function clampsTo(day, isoDate) {
  if (!Number.isInteger(day)) {
    return false;
  }
  const { year, month, day: startDay } = parts(isoDate);
  // Day 0 of the next month is the last day of this one.
  const lastDayOfMonth = new Date(year, month, 0).getDate();
  return Math.min(day, lastDayOfMonth) === startDay;
}

function parts(isoDate) {
  const [year, month, day] = isoDate.split("-");
  return { year: Number(year), month: Number(month), day: Number(day) };
}

function today() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
