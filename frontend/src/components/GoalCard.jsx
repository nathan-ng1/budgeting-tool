import { useState } from "react";

import { useDateFormat, useMoney } from "../lib/settings.jsx";
import ContributionForm from "./ContributionForm.jsx";

const plural = (count, word) => `${count} ${word}${count === 1 ? "" : "s"}`;

const CHIP_TONES = { "On track": "good", Behind: "bad", Achieved: "good", Ended: "bad", Upcoming: "muted" };

export function StatusChip({ flag }) {
  return <span className={`goals__chip goals__chip--${CHIP_TONES[flag] ?? "muted"}`}>{flag}</span>;
}

// The progress bar, with a tick where an even pace would have the Goal today.
// The tick only means something while the Goal is Active.
export function ProgressBar({ goal }) {
  return (
    <div
      className="goals__bar"
      role="progressbar"
      aria-label={`${goal.title} progress`}
      aria-valuenow={Math.round(goal.fraction * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className={`goals__bar-fill goals__bar-fill--${goal.flag === "Behind" ? "behind" : "ok"}`}
        style={{ width: `${goal.fraction * 100}%` }}
      />
      {goal.status === "Active" && (
        <div
          className="goals__bar-pace"
          style={{ left: `${goal.pace_fraction * 100}%` }}
          title="Where an even pace would have you today"
        />
      )}
    </div>
  );
}

export default function GoalCard({ goal, today, onEdit, onAddContribution, onArchive, onDelete, onDetails }) {
  const { money } = useMoney();
  const { dayMonthYear } = useDateFormat();
  const [contributing, setContributing] = useState(false);

  let headline;
  let sub;
  if (goal.status === "Achieved") {
    headline = "Goal reached";
    sub = goal.over > 0 ? `+${money(goal.over)} over target` : "Fully funded";
  } else if (goal.status === "Ended") {
    headline = `${money(goal.remaining)} short`;
    sub = `Ended ${dayMonthYear(goal.end_date)}. Edit the end date to extend it.`;
  } else {
    headline = `Save ${money(goal.required_per_month)} / month`;
    sub = `to finish by ${dayMonthYear(goal.end_date)} (${plural(goal.months_left, "month")} left)`;
  }

  return (
    <section className="card goals__card">
      <div className="goals__card-top">
        <h3>{goal.title}</h3>
        <StatusChip flag={goal.flag} />
      </div>
      {goal.description && <p className="goals__muted goals__clamp">{goal.description}</p>}
      <div className="goals__headline numeric">{headline}</div>
      <div className="goals__muted">{sub}</div>
      <ProgressBar goal={goal} />
      <div className="goals__row">
        <span className="numeric">
          {money(goal.saved)} of {money(goal.target_amount)}
        </span>
        <span className="numeric">{Math.round((goal.saved / goal.target_amount) * 100)}%</span>
      </div>
      {goal.status !== "Achieved" && goal.status !== "Ended" && (
        <div className="goals__muted">Original plan: {money(goal.original_plan_per_month)} / month</div>
      )}
      {contributing && (
        <ContributionForm
          goal={goal}
          today={today}
          onSave={async (contribution) => {
            await onAddContribution(goal, contribution);
            setContributing(false);
          }}
          onCancel={() => setContributing(false)}
        />
      )}
      <div className="goals__actions">
        <button type="button" className="button" onClick={() => setContributing(true)}>
          Add contribution
        </button>
        <button type="button" className="button button--quiet" onClick={onEdit}>
          Edit
        </button>
        <button type="button" className="button button--quiet" onClick={onArchive}>
          Archive
        </button>
        <button type="button" className="button button--quiet" onClick={onDelete}>
          Delete
        </button>
      </div>
      <button type="button" className="button goals__details-button" onClick={onDetails}>
        Details
      </button>
    </section>
  );
}
