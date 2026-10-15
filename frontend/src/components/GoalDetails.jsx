import { plural } from "../lib/goalFigures.js";
import { useDateFormat, useMoney } from "../lib/settings.jsx";
import { StatusChip } from "./GoalCard.jsx";
import GoalTrajectory from "./GoalTrajectory.jsx";

// The headline, drawn as a pill beside the way back: what it takes each month,
// or how the Goal finished. It sits outside the stats strip so a long figure
// (the Achieved case especially) never has to fit a strip column; `note` is a
// small line under the figure, when there is one.
function headline(goal, money) {
  if (goal.required_per_month !== null) {
    return { label: "You need to save", value: `${money(goal.required_per_month)} / month`, note: null };
  }
  if (goal.status === "Achieved") {
    return { label: "Status", value: "Goal reached", note: goal.over > 0 ? `+${money(goal.over)} over target` : null };
  }
  return { label: "Shortfall", value: `${money(goal.remaining)} short`, note: null };
}

// What "Remaining time" says: the months left, or - once the end date has
// passed - how the Goal finished (Achieved or Ended).
function remainingTime(goal) {
  return goal.months_left > 0 ? plural(goal.months_left, "month") : goal.status;
}

// One Goal in focus (Goals spec section 10): stats, trajectory and Contributions.
// Read-only on purpose - a Contribution is edited on the Transactions tab - so
// the only control is the way back to the grid.
export default function GoalDetails({ goal, today, onBack }) {
  const { money } = useMoney();
  const { dayMonthYear } = useDateFormat();
  const lead = headline(goal, money);

  const stats = [
    ["Saved", `${money(goal.saved)} of ${money(goal.target_amount)}`],
    ["Left", money(goal.remaining)],
    ["Remaining time", remainingTime(goal)],
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
        <div className="goals__details-head-right">
          <div className="goals__pill" aria-label="Goal headline">
            <div className="goals__pill-label">{lead.label}</div>
            <div className="goals__pill-value numeric">{lead.value}</div>
            {lead.note && <div className="goals__pill-note numeric">{lead.note}</div>}
          </div>
          <button type="button" className="button" onClick={onBack}>
            &larr; All goals
          </button>
        </div>
      </div>

      <dl className="goals__stats" aria-label="Goal stats">
        {stats.map(([label, value]) => (
          <div key={label}>
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
