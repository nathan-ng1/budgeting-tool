// Each Type's running total across its own Categories' Budgeted Amount
// (Issue #77) - shared by the per-month editor and the Full year read-only
// grid, which differ only in where the amounts come from. Kept out of the
// components so the summing is unit-testable without rendering a table, the
// same reasoning as budgetEditorForm.js.

// The per-month editor's Type totals, recomputed from `values` (not
// `editor`) so they stay live as the user types, before Save. A blank or
// invalid field contributes $0 to its Type's total - the same "unset != $0
// but sums as $0" rule ADR-0013 already applies to the annual Budgeted sum.
export function totalsByType(editor, values) {
  const totals = {};
  for (const [type, rows] of Object.entries(editor)) {
    totals[type] = rows.reduce((sum, { category }) => sum + (Number(values[category]) || 0), 0);
  }
  return totals;
}

// The Full year grid's Type totals: one array per Type, summing each of its
// Categories' Category Budget amounts per month column (in the same
// July-to-June order BudgetGridRow.amounts already uses) - an unset month
// contributes $0.
export function gridTotalsByType(grid) {
  const totals = {};
  for (const [type, rows] of Object.entries(grid)) {
    const monthCount = rows[0]?.amounts.length ?? 0;
    totals[type] = Array.from({ length: monthCount }, (_, index) =>
      rows.reduce((sum, row) => sum + (row.amounts[index] ?? 0), 0),
    );
  }
  return totals;
}
