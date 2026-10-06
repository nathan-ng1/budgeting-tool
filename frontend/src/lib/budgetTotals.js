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

// gridTotalsByType's output transposed: one Type totals object per month
// column, the shape leftToBudget takes - so the Full year grid's Left to
// Budget row (#167) reads a column the same way the per-month editor reads
// totalsByType. A Type with no Categories (an empty array) counts as $0.
export function gridMonthTotals(totals, monthCount) {
  return Array.from({ length: monthCount }, (_, index) =>
    Object.fromEntries(Object.entries(totals).map(([type, amounts]) => [type, amounts[index] ?? 0])),
  );
}

// The Types a Left to Budget subtracts from budgeted Income (Issue #167) -
// every outflow, Savings included, so a plan that gives every dollar a job
// lands on exactly $0 (see GLOSSARY.md). Order matters to the editor's
// stacked meter, which draws its segments in this order.
export const OUTFLOW_TYPES = ["Expense", "Bills & Subscriptions", "Debt", "Savings"];

// Left to Budget from one month's Type totals (either totalsByType's live
// figures or one column of gridTotalsByType's). A Type missing from `totals`
// counts as $0, same as an unset field does inside totalsByType.
export function leftToBudget(totals) {
  const income = totals.Income ?? 0;
  const outflows = OUTFLOW_TYPES.reduce((sum, type) => sum + (totals[type] ?? 0), 0);
  return { income, outflows, left: income - outflows };
}
