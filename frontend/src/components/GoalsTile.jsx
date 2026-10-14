import { useEffect, useState } from "react";

import { fetchGoals } from "../lib/goalsApi.js";
import { percentFunded } from "../lib/goalFigures.js";
import { useMoney } from "../lib/settings.jsx";
import { ProgressBar, StatusChip } from "./GoalCard.jsx";

const TILE_SIZE = 3;

// What the "$X / month" slot says when there is no monthly figure to ask for:
// the Goal is Achieved or Ended, so say how it finished instead.
function monthlySlot(goal, money) {
  if (goal.required_per_month !== null) {
    return `${money(goal.required_per_month)} / month`;
  }
  return goal.status === "Achieved" ? "Goal reached" : `${money(goal.remaining)} short`;
}

// The Overview's Goals tile (Goals spec section 11): the top three active
// Goals - active in the lifecycle sense, so whatever the Goals endpoint lists
// as `goals` (Achieved, Ended and Upcoming included, Past goals not) - soonest
// end date first. Like the Goals tab it follows no month or
// Financial Year - a Goal's figures are all-time, from the Goals endpoint.
export default function GoalsTile({ onViewAll }) {
  const { money } = useMoney();
  const [goals, setGoals] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchGoals({ signal: controller.signal })
      .then((loaded) => setGoals(loaded.goals))
      .catch((cause) => {
        if (cause.name !== "AbortError") {
          setError(cause.message);
        }
      });
    return () => controller.abort();
  }, []);

  const active = [...(goals ?? [])].sort((a, b) => a.end_date.localeCompare(b.end_date));

  return (
    <section className="card goals-tile" aria-label="Goals">
      <div className="card__head">
        <h3>Goals</h3>
        <div className="card__aside">
          <div className="card__aside-figure numeric">{active.length}</div>
          <div className="card__aside-label">active</div>
        </div>
      </div>

      {error !== null && (
        <p className="state state--error" role="alert">
          {error}
        </p>
      )}
      {error === null && goals === null && <p className="state">Loading your goals&hellip;</p>}
      {error === null && goals !== null && active.length === 0 && <p className="state">No active goals yet.</p>}
      {active.length > 0 && (
        <ul className="goals-tile__list">
          {active.slice(0, TILE_SIZE).map((goal) => (
            <li key={goal.id}>
              <div className="goals__card-top">
                <h4>{goal.title}</h4>
                <StatusChip flag={goal.flag} />
              </div>
              <ProgressBar goal={goal} />
              <div className="goals__row goals__muted">
                <span className="numeric">{percentFunded(goal)}% funded</span>
                <span className="numeric">{monthlySlot(goal, money)}</span>
              </div>
            </li>
          ))}
        </ul>
      )}

      <button type="button" className="link-button" onClick={onViewAll}>
        View all goals
      </button>
    </section>
  );
}
