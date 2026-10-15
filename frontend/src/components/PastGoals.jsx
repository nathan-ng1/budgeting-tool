import { useMoney } from "../lib/settings.jsx";

const BADGES = { archived: "Archived", deleted: "Deleted" };

// The collapsed Past goals list (Goals spec section 10): archived and deleted
// Goals, each with its badge, saved of target and Reactivate. A Past goal takes
// no new Contribution, so there is no Add contribution here.
export default function PastGoals({ past, onReactivate }) {
  const { money } = useMoney();

  if (past.length === 0) {
    return null;
  }

  return (
    <details className="card goals__past">
      <summary>Past goals ({past.length})</summary>
      <ul className="goals__past-list">
        {past.map((goal) => (
          <li key={goal.id} className="goals__past-item">
            <span className="goals__past-title">{goal.title}</span>
            <span className="goals__chip goals__chip--muted">{BADGES[goal.state] ?? goal.state}</span>
            <span className="numeric goals__muted">
              {money(goal.saved)} of {money(goal.target_amount)}
            </span>
            <button type="button" className="button button--quiet" onClick={() => onReactivate(goal)}>
              Reactivate
            </button>
          </li>
        ))}
      </ul>
    </details>
  );
}
