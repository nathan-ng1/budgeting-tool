import { useDateFormat, useMoney } from "../lib/settings.jsx";
import { StatusChip } from "./GoalCard.jsx";
import GoalTrajectory from "./GoalTrajectory.jsx";

const plural = (count, word) => `${count} ${word}${count === 1 ? "" : "s"}`;

// The headline stat: what it takes each month, or how the Goal finished.
function headline(goal, money) {
  if (goal.required_per_month !== null) {
    return ["Needs", `${money(goal.required_per_month)} / month`];
  }
  if (goal.status === "Achieved") {
    return ["Status", goal.over > 0 ? `Reached, +${money(goal.over)} over` : "Reached"];
  }
  return ["Shortfall", money(goal.remaining)];
}

// One Goal in focus (Goals spec section 10): stats, trajectory and Contributions.
// Read-only on purpose - a Contribution is edited on the Transactions tab - so
// the only control is the way back to the grid.
export default function GoalDetails({ goal, today, onBack }) {
  const { money } = useMoney();
  const { dayMonthYear } = useDateFormat();
  const [lead, leadValue] = headline(goal, money);

  const stats = [
    [lead, leadValue],
    ["Saved", `${money(goal.saved)} of ${money(goal.target_amount)}`],
    ["Left", money(goal.remaining)],
    ["Remaining time", goal.months_left > 0 ? plural(goal.months_left, "month") : "Ended"],
    ["End date", dayMonthYear(goal.end_date)],
    ["Original plan", `${money(goal.original_plan_per_month)} / month`],
    ["Start date", dayMonthYear(goal.start_date)],
  ];

  return (
    <section className="card goals__details">
      <div className="card__head">
        <div>
          <div className="goals__details-title">
            <h3>{goal.title}</h3>
            <StatusChip flag={goal.flag} />
          </div>
          {goal.description && <p className="goals__muted">{goal.description}</p>}
        </div>
        <button type="button" className="button" onClick={onBack}>
          &larr; All goals
        </button>
      </div>

      <dl className="goals__stats" aria-label="Goal stats">
        {stats.map(([label, value], index) => (
          <div key={label} className={index === 0 ? "goals__stats-lead" : undefined}>
            <dt>{label}</dt>
            <dd className="numeric">{value}</dd>
          </div>
        ))}
      </dl>

      <GoalTrajectory goal={goal} today={today} />

      <h4 className="goals__details-sub">Contributions ({goal.contributions.length})</h4>
      {goal.contributions.length === 0 ? (
        <p className="state">No contributions yet.</p>
      ) : (
        <table className="recurring goals__ledger" aria-label="Contributions">
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Notes</th>
              <th scope="col" className="recurring__num">
                Amount
              </th>
            </tr>
          </thead>
          <tbody>
            {[...goal.contributions].reverse().map((contribution, index) => (
              <tr key={index}>
                <td>{dayMonthYear(contribution.date)}</td>
                <td>{contribution.notes}</td>
                <td className="recurring__num numeric">{money(contribution.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
