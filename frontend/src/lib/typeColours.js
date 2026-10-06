// One fill per outflow Type, so a Type reads as the same colour on the
// Overview's "Where did my income go?" bar (IncomeAllocation.jsx) and the
// Budget tab's Left to Budget meter (LeftToBudget.jsx) - spec #164. Keyed by
// Type name (GLOSSARY.md); Income has no fill of its own, it's the axis.
export const TYPE_COLOURS = {
  Expense: "var(--color-negative-fill)",
  "Bills & Subscriptions": "var(--color-bills-subscriptions)",
  Debt: "var(--color-debt)",
  Savings: "var(--color-savings)",
};
