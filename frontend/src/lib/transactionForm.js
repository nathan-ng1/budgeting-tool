// Form state for one Transaction (Issue #35) - mirrors ruleForm.js, but a
// Transaction carries no schedule to derive, so there is no Day/Frequency
// dance: Type still narrows which Categories are valid (ADR-0006).
//
// The Goals Category adds a Goal link (Goals spec section 5, ADR-0031): the
// form holds it as `goalId` (a select value, so a string, "" for none).
// `currentGoal` is the Goal the row already points at when editing, so its
// picker can still offer a Goal that is no longer active. `autoNotes` is the
// Goal title last typed into Notes on the user's behalf, so a later Goal
// change can replace it - but never text the user wrote.

// The Category whose Transactions are Contributions to a Goal.
export const GOALS_CATEGORY = "Goals";

export function blankValues(date = today()) {
  return {
    date,
    amount: "",
    type: "Expense",
    category: "",
    notes: "",
    goalId: "",
    currentGoal: null,
    autoNotes: "",
  };
}

export function valuesFrom(transaction) {
  const linked = transaction.goal_id !== null && transaction.goal_id !== undefined;
  return {
    date: transaction.date,
    amount: String(transaction.amount),
    type: transaction.type,
    category: transaction.category,
    notes: transaction.notes,
    goalId: linked ? String(transaction.goal_id) : "",
    currentGoal: linked
      ? { id: transaction.goal_id, title: transaction.goal_title, state: transaction.goal_state ?? "active" }
      : null,
    autoNotes: "",
  };
}

export function withType(values, type, categoriesByType) {
  const allowed = categoriesByType[type] ?? [];
  // A Category belongs to exactly one Type (ADR-0006), so changing Type
  // always invalidates the Category unless the form is being rebuilt. The
  // default is never Goals, which needs a Goal chosen (and may have none).
  const fallback = allowed.find((name) => name !== GOALS_CATEGORY) ?? allowed[0] ?? "";
  return withCategory({ ...values, type }, allowed.includes(values.category) ? values.category : fallback);
}

// Leaving the Goals Category drops the Goal link: the store refuses a
// payload that keeps it.
export function withCategory(values, category) {
  return { ...values, category, goalId: category === GOALS_CATEGORY ? values.goalId : "" };
}

// Picking a Goal. When `defaultNotes` (adding, never editing), Notes follow
// the Goal's title unless the user has written their own.
export function withGoal(values, goalId, options, { defaultNotes }) {
  const goal = options.find((option) => String(option.id) === goalId);
  const next = { ...values, goalId };
  if (defaultNotes && goal !== undefined && (values.notes === "" || values.notes === values.autoNotes)) {
    next.notes = goal.title;
    next.autoNotes = goal.title;
  }
  return next;
}

// The picker's Goals: every active Goal, plus the row's own Goal when it is
// no longer active (marked, so it reads as past).
export function goalOptions(activeGoals, currentGoal) {
  const options = activeGoals.map((goal) => ({ id: goal.id, title: goal.title, label: goal.title }));
  if (currentGoal && !options.some((option) => option.id === currentGoal.id)) {
    const suffix = currentGoal.state === "active" ? "" : ` (${currentGoal.state})`;
    options.unshift({ id: currentGoal.id, title: currentGoal.title, label: `${currentGoal.title}${suffix}` });
  }
  return options;
}

export function toPayload(values) {
  return {
    date: values.date,
    amount: Number(values.amount),
    type: values.type,
    category: values.category,
    notes: values.notes,
    goal_id: values.category === GOALS_CATEGORY && values.goalId !== "" ? Number(values.goalId) : null,
  };
}

function today() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}
