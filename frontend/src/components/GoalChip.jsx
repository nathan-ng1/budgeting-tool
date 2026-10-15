// The linked Goal's current title, shown beside a Goals-Category row's
// Category (Goals spec section 5). Not clickable. A Goal that has since been
// archived or deleted shows muted, with its state.
export default function GoalChip({ title, state = "active" }) {
  if (title === null || title === undefined) {
    return null;
  }

  const past = state !== "active";
  return (
    <span className={past ? "goal-chip goal-chip--muted" : "goal-chip"}>
      {past ? `${title} (${state})` : title}
    </span>
  );
}
