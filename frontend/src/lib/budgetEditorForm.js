// Pure helpers behind the Budget tab's per-month editor (Issue #62) - kept
// separate from Budget.jsx so the diffing behind "Save only what changed"
// (ADR-0013: unset != $0) is unit-testable without rendering a table.

// The editor endpoint's response, grouped by Type - see dashboard.budgets.
// Flattened into one category -> string map for the form's inputs: an unset
// Category Budget renders as "" (blank), never "0" or "null".
export function valuesFrom(editor) {
  const values = {};
  for (const rows of Object.values(editor)) {
    for (const { category, amount } of rows) {
      values[category] = amount === null ? "" : String(amount);
    }
  }
  return values;
}

// Every Category whose current value differs from what the editor loaded
// with, as a { category, amount } pair - `amount` is null for a field
// cleared back to blank (a delete), or the typed number otherwise.
export function changesFrom(initial, values) {
  const changes = [];
  for (const category of Object.keys(values)) {
    const before = initial[category] ?? "";
    const after = values[category];
    if (before === after) {
      continue;
    }
    changes.push({ category, amount: after === "" ? null : Number(after) });
  }
  return changes;
}
