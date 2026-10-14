// PROTOTYPE (issue #209) - throwaway. Variant A "Cards": one card per Goal in a grid, the
// monthly figure as the headline of each card, split tool as a slide-down panel.
import { useState } from "react";

import { useMoney } from "../../lib/settings.jsx";
import GoalForm from "./GoalForm.jsx";
import { byStatus, describeGoal, fmtDate, todayISO } from "./goalsMath.js";
import { actions, useGoals } from "./store.js";
import useSplit from "./useSplit.js";
import Trajectory from "./Trajectory.jsx";

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

function Bar({ d }) {
  return (
    <div className="gp-bar" role="progressbar" aria-valuenow={Math.round(d.fraction * 100)} aria-valuemin={0} aria-valuemax={100}>
      <div className={`gp-bar__fill gp-bar__fill--${d.flag === "Behind" ? "behind" : "ok"}`} style={{ width: `${d.fraction * 100}%` }} />
      {d.status === "Active" && <div className="gp-bar__pace" style={{ left: `${d.paceFraction * 100}%` }} title="Where an even pace would have you today" />}
    </div>
  );
}

function Chip({ flag }) {
  const tone = { "On track": "good", Behind: "bad", Achieved: "good", Ended: "bad", Upcoming: "muted" }[flag] ?? "muted";
  return <span className={`gp-chip gp-chip--${tone}`}>{flag}</span>;
}

function GoalCard({ d, onEdit, onDetails }) {
  const { money } = useMoney();
  const [adding, setAdding] = useState(false);
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(todayISO());
  const { goal } = d;

  let headline;
  let sub;
  if (d.status === "Achieved") {
    headline = "Goal reached";
    sub = d.over > 0 ? `+${money(d.over)} over target` : "Fully funded";
  } else if (d.status === "Ended") {
    headline = `${money(d.remaining)} short`;
    sub = `Ended ${fmtDate(goal.end)}. Edit the end date to extend it.`;
  } else {
    headline = `Save ${money(d.requiredPerMonth)} / month`;
    sub = `to finish by ${fmtDate(goal.end)} (${plural(d.monthsLeft, "month")} left)`;
  }

  return (
    <section className="card gp-card">
      <div className="gp-card__top">
        <h3>{goal.title}</h3>
        <Chip flag={d.flag} />
      </div>
      {goal.description && <p className="gp-muted gp-clamp">{goal.description}</p>}
      <div className="gp-headline numeric">{headline}</div>
      <div className="gp-muted">{sub}</div>
      <Bar d={d} />
      <div className="gp-row">
        <span className="numeric">
          {money(d.saved)} of {money(goal.target)}
        </span>
        <span className="numeric">{Math.round((d.saved / goal.target) * 100)}%</span>
      </div>
      {d.status !== "Achieved" && d.status !== "Ended" && (
        <div className="gp-muted gp-hint">Original plan: {money(d.originalPlan)} / month</div>
      )}

      {adding ? (
        <form
          className="gp-inline"
          onSubmit={(e) => {
            e.preventDefault();
            if (Number(amount) > 0) {
              actions.addContribution(goal.id, { amount: Number(amount), date });
              setAdding(false);
              setAmount("");
            }
          }}
        >
          <input aria-label="Amount" type="number" step="0.01" min="0" placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} autoFocus />
          <input aria-label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <button className="button" type="submit">Add</button>
          <button className="button button--quiet" type="button" onClick={() => setAdding(false)}>Cancel</button>
        </form>
      ) : (
        <div className="gp-actions">
          <button className="button button--quiet" type="button" onClick={() => setAdding(true)}>Add contribution</button>
          <button className="button button--quiet" type="button" onClick={onEdit}>Edit</button>
          <button className="button button--quiet" type="button" onClick={() => actions.archive(goal.id)}>Archive</button>
          <button className="button button--quiet button--danger" type="button" onClick={() => actions.remove(goal.id)}>Delete</button>
        </div>
      )}
      <button className="button gp-details-btn" type="button" onClick={onDetails}>Details</button>
    </section>
  );
}

// The "Details" view: one Goal in focus - stats, trajectory chart and the contributions ledger.
// Read-only on purpose: adding a contribution, editing, archiving and deleting all live on the
// Goal cards, so this page has no actions of its own beyond going back.
function GoalDetail({ d, contributions, onBack }) {
  const { money } = useMoney();
  const { goal } = d;
  const own = contributions.filter((c) => c.goalId === goal.id).sort((a, b) => b.date.localeCompare(a.date));

  return (
    <section className="card gp-detail-a">
      <div className="card__head">
        <div>
          <div className="gp-detail-a__title">
            <h3>{goal.title}</h3>
            <Chip flag={d.flag} />
          </div>
          {goal.description && <p className="gp-muted">{goal.description}</p>}
        </div>
        <button className="button" type="button" onClick={onBack}>&larr; All goals</button>
      </div>

      <dl className="gp-stats">
        <div className="gp-stats__lead">
          <dt>{d.requiredPerMonth !== null ? "Needs" : d.status === "Achieved" ? "Status" : "Shortfall"}</dt>
          <dd className="numeric">
            {d.requiredPerMonth !== null
              ? `${money(d.requiredPerMonth)} / month`
              : d.status === "Achieved"
                ? d.over > 0 ? `Reached, +${money(d.over)} over` : "Reached"
                : money(d.remaining)}
          </dd>
        </div>
        <div>
          <dt>Saved</dt>
          <dd className="numeric">{money(d.saved)} <span className="gp-muted">of {money(goal.target)}</span></dd>
        </div>
        <div><dt>Left</dt><dd className="numeric">{money(d.remaining)}</dd></div>
        <div><dt>Remaining time</dt><dd>{d.monthsLeft > 0 ? plural(d.monthsLeft, "month") : "Ended"}</dd></div>
        <div><dt>End date</dt><dd>{fmtDate(goal.end)}</dd></div>
        <div><dt>Original plan</dt><dd className="numeric">{money(d.originalPlan)} / month</dd></div>
        <div><dt>Start date</dt><dd>{fmtDate(goal.start)}</dd></div>
      </dl>

      <Trajectory d={d} contributions={contributions} />

      <h4 className="gp-detail-a__sub">Contributions ({own.length})</h4>
      {own.length === 0 ? (
        <p className="state">No contributions yet.</p>
      ) : (
        <div className="gp-ledger">
          <div className="gp-ledger__row gp-ledger__head">
            <span>Date</span>
            <span>Notes</span>
            <span className="gp-ledger__amount">Amount</span>
          </div>
          {own.map((c) => (
            <div key={c.id} className="gp-ledger__row">
              <span>{fmtDate(c.date)}</span>
              <span>{c.notes}</span>
              <span className="gp-ledger__amount numeric">{money(c.amount)}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function SplitPanel({ activeGoals, onClose }) {
  const { money } = useMoney();
  const s = useSplit(activeGoals);
  return (
    <section className="card gp-panel">
      <div className="card__head">
        <h3>Split savings across Goals</h3>
        <button className="link-button" type="button" onClick={onClose}>Close</button>
      </div>
      <div className="gp-split-top">
        <label className="field">
          <span className="field__label">Total to allocate</span>
          <input type="number" step="0.01" min="0" value={s.total} onChange={(e) => s.setTotal(e.target.value)} />
        </label>
        <label className="field">
          <span className="field__label">Date</span>
          <input type="date" value={s.date} onChange={(e) => s.setDate(e.target.value)} />
        </label>
        <button className="button button--quiet" type="button" onClick={() => s.setTotal(String(s.unallocated))}>
          Use this month's Unallocated ({money(s.unallocated)})
        </button>
      </div>
      <div className="gp-split-rows">
        {activeGoals.map((g) => (
          <label key={g.id} className="gp-split-row">
            <span>{g.title}</span>
            <span className="gp-pct">
              <input type="number" min="0" max="100" step="1" value={s.percentOf(g.id)} onChange={(e) => s.setPercent(g.id, e.target.value)} />%
            </span>
          </label>
        ))}
        <div className="gp-split-row gp-split-row--rest">
          <span>
            Everything else, saved as{" "}
            <select value={s.restCategory} onChange={(e) => s.setRestCategory(e.target.value)} aria-label="Remainder Category">
              <option>Savings</option>
              <option>Investments</option>
            </select>
          </span>
          <span className="numeric">{s.restPct.toFixed(0)}%</span>
        </div>
      </div>
      {s.overCap && <p className="field__hint field__hint--error" role="alert">Percentages add up to {s.used}% - the cap is 100%.</p>}
      {s.preview && (
        <ul className="gp-preview">
          {s.preview.goals.map((p) => (
            <li key={p.goal.id}>
              <span>Goals · {p.goal.title}</span>
              <span className="numeric">{money(p.amount)}</span>
            </li>
          ))}
          {s.preview.rest.amount > 0 && (
            <li>
              <span>{s.restCategory}</span>
              <span className="numeric">{money(s.preview.rest.amount)}</span>
            </li>
          )}
        </ul>
      )}
      <div className="rule-form__actions">
        <button className="button" type="button" disabled={!s.canApply} onClick={() => { s.apply(); onClose(); }}>
          Write transactions
        </button>
      </div>
    </section>
  );
}

export function TabA() {
  const { goals, contributions, lastSplit } = useGoals();
  const { money } = useMoney();
  const [panel, setPanel] = useState(null); // "new" | "split" | { edit: id, reactivate?: true }
  const [detailId, setDetailId] = useState(null);

  const live = goals.filter((g) => !g.past).map((g) => describeGoal(g, contributions)).sort(byStatus);
  const past = goals.filter((g) => g.past);
  const active = live.filter((d) => d.status === "Active").map((d) => d.goal);
  const savedToGoals = live.reduce((s, d) => s + d.saved, 0);
  const editing = panel?.edit ? goals.find((g) => g.id === panel.edit) : null;
  // A Goal archived or deleted from its detail view drops out of `live`, which closes it.
  const detail = detailId === null ? null : live.find((d) => d.goal.id === detailId) ?? null;

  return (
    <div className="gp gp-a">
      {detail === null && (
      <section className="card">
        <div className="card__head">
          <div>
            <h3>Goals</h3>
            <div className="gp-muted">
              {plural(active.length, "active goal")} · {money(savedToGoals)} saved toward goals
            </div>
          </div>
          <div className="gp-actions">
            <button className="button button--quiet" type="button" onClick={() => setPanel("split")} disabled={active.length === 0}>Split savings</button>
            <button className="button" type="button" onClick={() => setPanel("new")}>New goal</button>
          </div>
        </div>
      </section>
      )}

      {lastSplit && (
        <p className="state state--page" role="status">
          Wrote {plural(lastSplit.length, "transaction")}: {lastSplit.map((t) => `${t.notes} ${money(t.amount)}`).join(" · ")}{" "}
          <button className="link-button" type="button" onClick={actions.clearLastSplit}>Dismiss</button>
        </p>
      )}

      {panel === "new" && <GoalForm goals={goals} onCancel={() => setPanel(null)} onSave={(f) => { actions.addGoal(f); setPanel(null); }} />}
      {editing && (
        <GoalForm
          goals={goals}
          initial={editing}
          submitLabel={panel.reactivate ? "Reactivate goal" : "Save goal"}
          onCancel={() => setPanel(null)}
          onSave={(f) => {
            actions.updateGoal(editing.id, f);
            if (panel.reactivate) actions.reactivate(editing.id);
            setPanel(null);
          }}
        />
      )}
      {panel === "split" && <SplitPanel activeGoals={active} onClose={() => setPanel(null)} />}

      {detail !== null && (
        <GoalDetail
          d={detail}
          contributions={contributions}
          onBack={() => setDetailId(null)}
        />
      )}

      {detail === null && (
        <div className="gp-grid">
          {live.map((d) => (
            <GoalCard key={d.goal.id} d={d} onEdit={() => setPanel({ edit: d.goal.id })} onDetails={() => setDetailId(d.goal.id)} />
          ))}
        </div>
      )}

      {detail === null && (
      <details className="card gp-past">
        <summary>Past goals ({past.length})</summary>
        {past.length === 0 && <p className="state">Nothing here yet.</p>}
        {past.map((g) => {
          const d = describeGoal({ ...g, past: null }, contributions);
          return (
            <div key={g.id} className="gp-past__row">
              <span>
                {g.title} <span className="gp-chip gp-chip--muted">{g.past === "archived" ? "Archived" : "Deleted"}</span>
              </span>
              <span className="numeric gp-muted">
                {money(d.saved)} of {money(g.target)}
              </span>
              <button className="button button--quiet" type="button" onClick={() => setPanel({ edit: g.id, reactivate: true })}>
                Reactivate
              </button>
            </div>
          );
        })}
      </details>
      )}
    </div>
  );
}

export function TileA({ onViewAll }) {
  const { goals, contributions } = useGoals();
  const { money } = useMoney();
  const live = goals
    .filter((g) => !g.past)
    .map((g) => describeGoal(g, contributions))
    .filter((d) => d.status === "Active")
    .sort((a, b) => a.goal.end.localeCompare(b.goal.end));
  const top = live.slice(0, 3);
  return (
    <section className="card gp-tile-a">
      <div className="card__head">
        <h3>Goals</h3>
        <div className="card__aside">
          <div className="card__aside-figure numeric">{live.length}</div>
          <div className="card__aside-label">active</div>
        </div>
      </div>
      {top.length === 0 ? (
        <p className="state">No active goals yet.</p>
      ) : (
        <ul className="gp-tile-a__list">
          {top.map((d) => (
            <li key={d.goal.id}>
              <div className="gp-row">
                <strong>{d.goal.title}</strong>
                <Chip flag={d.flag} />
              </div>
              <Bar d={d} />
              <div className="gp-row gp-muted">
                <span className="numeric">{Math.round(d.fraction * 100)}% funded</span>
                <span className="numeric">{money(d.requiredPerMonth)} / month</span>
              </div>
            </li>
          ))}
        </ul>
      )}
      <button className="link-button" type="button" onClick={onViewAll}>View all goals</button>
    </section>
  );
}
