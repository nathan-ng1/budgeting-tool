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

// The three Types that make up Outflows (GLOSSARY.md), in stacking order;
// Savings is deliberately absent - it's what's left to keep, not something
// spent. `key` is the field on the Overview's stat tiles / monthly totals.
export const OUTFLOW_SERIES = [
  { key: "expenses", label: "Expenses", colour: TYPE_COLOURS.Expense },
  { key: "bills_subscriptions", label: "Bills & Subscriptions", colour: TYPE_COLOURS["Bills & Subscriptions"] },
  { key: "debt", label: "Debt", colour: TYPE_COLOURS.Debt },
];
