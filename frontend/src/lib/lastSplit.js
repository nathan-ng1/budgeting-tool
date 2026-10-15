// The percentages of the last Split savings, remembered in the browser as a
// prefill for the next one (Goals spec section 9) - a prefill, not a standing
// rule. Like the theme and period type it is a UI preference, so it lives in
// localStorage rather than the Database. Keyed by Goal id: a Goal that no
// longer exists is simply never asked for.

const STORAGE_KEY = "budgeting-tool:last-split";

// { [goalId]: percent }, or {} when nothing usable is stored.
export function loadLastSplit() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
    return stored && typeof stored === "object" && !Array.isArray(stored) ? stored : {};
  } catch {
    return {};
  }
}

export function saveLastSplit(percents) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(percents));
  } catch {
    // Storage full or blocked: the prefill is a nicety, so losing it is fine.
  }
}
