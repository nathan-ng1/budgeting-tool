// Small helpers shared by the Goals tab, its Details view and the Overview tile.

export const STATUS_ACTIVE = "Active";

// "1 month", "3 months".
export const plural = (count, word) => `${count} ${word}${count === 1 ? "" : "s"}`;

// How funded a Goal is, as a whole percent. Built from the server's `fraction`
// (saved over target, capped at 1) so the number, the progress bar and the
// Overview tile always agree; money over the target is shown as "over" instead.
export const percentFunded = (goal) => Math.round(goal.fraction * 100);
