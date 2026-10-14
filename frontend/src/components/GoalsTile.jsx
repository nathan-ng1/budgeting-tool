import { useEffect, useState } from "react";

import { fetchGoals } from "../lib/goalsApi.js";
import { useMoney } from "../lib/settings.jsx";
import { ProgressBar, StatusChip } from "./GoalCard.jsx";

const TILE_SIZE = 3;

// The Overview's Goals tile (Goals spec section 11): the top three active
// Goals, soonest end date first. Like the Goals tab it follows no month or
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

  const active = (goals ?? [])
    .filter((goal) => goal.status === "Active")
    .sort((a, b) => a.end_date.localeCompare(b.end_date));

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
                <span className="numeric">{Math.round(goal.fraction * 100)}% funded</span>
                <span className="numeric">{money(goal.required_per_month)} / month</span>
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
