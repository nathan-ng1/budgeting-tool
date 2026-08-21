// Form state for one Transaction (Issue #35) - mirrors ruleForm.js, but a
// Transaction carries no schedule to derive, so there is no Day/Frequency
// dance: Type still narrows which Categories are valid (ADR-0006).

export function blankValues(date = today()) {
  return {
    date,
    amount: "",
    type: "Expense",
    category: "",
    notes: "",
  };
}

export function valuesFrom(transaction) {
  return {
    date: transaction.date,
    amount: String(transaction.amount),
    type: transaction.type,
    category: transaction.category,
    notes: transaction.notes,
  };
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
    date: values.date,
    amount: Number(values.amount),
    type: values.type,
    category: values.category,
    notes: values.notes,
  };
}

function today() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
