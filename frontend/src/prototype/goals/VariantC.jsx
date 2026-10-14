// PROTOTYPE (issue #209) - throwaway. Variant C "Master-detail": a slim Goal list on the left,
// one Goal in focus on the right with a saved-vs-even-pace trajectory chart. The split tool is
// a three-step wizard (amount -> percentages -> review) that takes over the right pane.
import { useState } from "react";

import { useMoney } from "../../lib/settings.jsx";
import GoalForm from "./GoalForm.jsx";
import { byStatus, describeGoal, fmtDate, fromISO, todayISO } from "./goalsMath.js";
import { actions, useGoals } from "./store.js";
import Trajectory from "./Trajectory.jsx";
import useSplit from "./useSplit.js";

function Ring({ d, size = 44 }) {
  const r = size / 2 - 4;
  const c = 2 * Math.PI * r;
  const tone = d.flag === "Behind" || d.flag === "Ended" ? "var(--color-negative)" : "var(--color-positive)";
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--color-neutral-300)" strokeWidth="5" />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={tone}
        strokeWidth="5"
        strokeLinecap="round"
        strokeDasharray={`${c * d.fraction} ${c}`}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text x="50%" y="50%" dominantBaseline="central" textAnchor="middle" fontSize={size / 4} fill="var(--color-text)">
        {Math.round(d.fraction * 100)}
      </text>
    </svg>
  );
}

function Wizard({ active, onClose }) {
  const { money } = useMoney();
  const s = useSplit(active);
  const [step, setStep] = useState(1);
  return (
    <div className="gp-wizard">
      <div className="card__head">
        <h3>Split savings · step {step} of 3</h3>
        <button className="link-button" type="button" onClick={onClose}>Cancel</button>
      </div>
      {step === 1 && (
        <>
          <p className="gp-muted">How much are you setting aside? It starts from this month's Unallocated - income not yet spent or saved.</p>
          <div className="gp-split-top">
            <label className="field">
              <span className="field__label">Total to allocate</span>
              <input type="number" step="0.01" min="0" value={s.total} onChange={(e) => s.setTotal(e.target.value)} />
            </label>
            <label className="field">
              <span className="field__label">Date</span>
              <input type="date" value={s.date} onChange={(e) => s.setDate(e.target.value)} />
            </label>
          </div>
          <p className="gp-muted">Unallocated this month: {money(s.unallocated)}</p>
          <button className="button" type="button" disabled={!(Number(s.total) > 0)} onClick={() => setStep(2)}>Next</button>
        </>
      )}
      {step === 2 && (
        <>
          <div className="gp-stack" aria-hidden="true">
            {active.map((g, i) => (
              <span key={g.id} className={`gp-stack__seg gp-stack__seg--${i % 4}`} style={{ width: `${Math.min(Number(s.percentOf(g.id)) || 0, 100)}%` }} />
            ))}
            <span className="gp-stack__seg gp-stack__seg--rest" style={{ width: `${s.restPct}%` }} />
          </div>
          <div className="gp-split-rows">
            {active.map((g, i) => (
              <label key={g.id} className="gp-split-row">
                <span><i className={`gp-swatch gp-stack__seg--${i % 4}`} /> {g.title}</span>
                <span className="gp-pct">
                  <input type="number" min="0" max="100" value={s.percentOf(g.id)} onChange={(e) => s.setPercent(g.id, e.target.value)} />%
                </span>
              </label>
            ))}
            <div className="gp-split-row gp-split-row--rest">
              <span>
                <i className="gp-swatch gp-stack__seg--rest" /> Everything else →{" "}
                <select value={s.restCategory} onChange={(e) => s.setRestCategory(e.target.value)} aria-label="Remainder Category">
                  <option>Savings</option>
                  <option>Investments</option>
                </select>
              </span>
              <span className="numeric">{s.restPct.toFixed(0)}%</span>
            </div>
          </div>
          {s.overCap && <p className="field__hint field__hint--error" role="alert">That adds up to {s.used}%. The most you can assign is 100%.</p>}
          <div className="gp-actions">
            <button className="button button--quiet" type="button" onClick={() => setStep(1)}>Back</button>
            <button className="button" type="button" disabled={!s.canApply} onClick={() => setStep(3)}>Review</button>
          </div>
        </>
      )}
      {step === 3 && s.preview && (
        <>
          <p className="gp-muted">These {s.preview.goals.length + (s.preview.rest.amount > 0 ? 1 : 0)} Savings transactions will be written on {fmtDate(s.date)}:</p>
          <ul className="gp-preview">
            {s.preview.goals.map((p) => (
              <li key={p.goal.id}>
                <span>Goals → {p.goal.title}</span>
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
          <div className="gp-actions">
            <button className="button button--quiet" type="button" onClick={() => setStep(2)}>Back</button>
            <button className="button" type="button" onClick={() => { s.apply(); onClose(); }}>Write transactions</button>
          </div>
        </>
      )}
    </div>
  );
}

export function TabC() {
  const { goals, contributions, lastSplit } = useGoals();
  const { money } = useMoney();
  const live = goals.filter((g) => !g.past).map((g) => describeGoal(g, contributions)).sort(byStatus);
  const past = goals.filter((g) => g.past);
  const active = live.filter((d) => d.status === "Active").map((d) => d.goal);
  const [sel, setSel] = useState(live[0]?.goal.id ?? null);
  const [view, setView] = useState("goal"); // goal | split | new | { edit, reactivate }
  const [amount, setAmount] = useState("");
  const [showPast, setShowPast] = useState(false);

  const focus = live.find((d) => d.goal.id === sel) ?? live[0] ?? null;
  const editing = view?.edit ? goals.find((g) => g.id === view.edit) : null;
  const own = focus ? contributions.filter((c) => c.goalId === focus.goal.id).sort((a, b) => b.date.localeCompare(a.date)) : [];

  return (
    <div className="gp gp-c">
      <aside className="card gp-c__list">
        <div className="card__head">
          <h3>Goals</h3>
          <button className="button" type="button" onClick={() => setView("new")}>New</button>
        </div>
        <ul>
          {live.map((d) => (
            <li key={d.goal.id}>
              <button type="button" className="gp-c__item" aria-current={focus?.goal.id === d.goal.id && view === "goal" ? "true" : undefined} onClick={() => { setSel(d.goal.id); setView("goal"); }}>
                <Ring d={d} />
                <span>
                  <strong>{d.goal.title}</strong>
                  <span className="gp-muted">{d.flag}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
        <button className="button button--quiet gp-c__split" type="button" disabled={active.length === 0} onClick={() => setView("split")}>
          Split savings…
        </button>
        <button className="link-button" type="button" onClick={() => setShowPast((v) => !v)}>
          Past goals ({past.length}) {showPast ? "▴" : "▾"}
        </button>
        {showPast && (
          <ul className="gp-c__past">
            {past.map((g) => (
              <li key={g.id}>
                <span>
                  {g.title} <span className="gp-muted">· {g.past === "archived" ? "Archived" : "Deleted"}</span>
                </span>
                <button className="link-button" type="button" onClick={() => setView({ edit: g.id, reactivate: true })}>Reactivate</button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      <section className="card gp-c__detail">
        {lastSplit && (
          <p className="state state--page" role="status">
            Wrote {lastSplit.length} transactions ({lastSplit.map((t) => `${t.notes} ${money(t.amount)}`).join(", ")}).{" "}
            <button className="link-button" type="button" onClick={actions.clearLastSplit}>Dismiss</button>
          </p>
        )}
        {view === "split" && <Wizard active={active} onClose={() => setView("goal")} />}
        {view === "new" && <GoalForm goals={goals} onCancel={() => setView("goal")} onSave={(f) => { actions.addGoal(f); setView("goal"); }} />}
        {editing && (
          <GoalForm
            goals={goals}
            initial={editing}
            submitLabel={view.reactivate ? "Reactivate goal" : "Save goal"}
            onCancel={() => setView("goal")}
            onSave={(f) => {
              actions.updateGoal(editing.id, f);
              if (view.reactivate) actions.reactivate(editing.id);
              setView("goal");
            }}
          />
        )}
        {view === "goal" && focus && (
          <>
            <div className="card__head">
              <div>
                <h3>{focus.goal.title}</h3>
                {focus.goal.description && <p className="gp-muted">{focus.goal.description}</p>}
              </div>
              <span className={`gp-chip gp-chip--${focus.flag === "Behind" || focus.flag === "Ended" ? "bad" : focus.flag === "Upcoming" ? "muted" : "good"}`}>{focus.flag}</span>
            </div>
            <dl className="gp-stats">
              <div className="gp-stats__lead">
                <dt>{focus.requiredPerMonth === null ? (focus.status === "Achieved" ? "Status" : "Shortfall") : "Needs"}</dt>
                <dd className="numeric">
                  {focus.requiredPerMonth !== null ? `${money(focus.requiredPerMonth)} / month` : focus.status === "Achieved" ? (focus.over > 0 ? `Reached, +${money(focus.over)}` : "Reached") : money(focus.remaining)}
                </dd>
              </div>
              <div><dt>Saved</dt><dd className="numeric">{money(focus.saved)} <span className="gp-muted">of {money(focus.goal.target)}</span></dd></div>
              <div><dt>Left</dt><dd className="numeric">{money(focus.remaining)}</dd></div>
              <div><dt>Time</dt><dd>{focus.monthsLeft > 0 ? `${focus.monthsLeft} month${focus.monthsLeft === 1 ? "" : "s"} to ${fmtDate(focus.goal.end)}` : `Ended ${fmtDate(focus.goal.end)}`}</dd></div>
              <div><dt>Original plan</dt><dd className="numeric">{money(focus.originalPlan)} / month</dd></div>
            </dl>
            <Trajectory d={focus} contributions={contributions} />
            <p className="gp-muted gp-legend">Solid: saved · dashed: even pace to target · vertical: today</p>

            <form
              className="gp-inline"
              onSubmit={(e) => {
                e.preventDefault();
                if (Number(amount) > 0) {
                  actions.addContribution(focus.goal.id, { amount: Number(amount), date: todayISO() });
                  setAmount("");
                }
              }}
            >
              <input aria-label="Contribution amount" type="number" step="0.01" min="0" placeholder="Add a contribution today" value={amount} onChange={(e) => setAmount(e.target.value)} />
              <button className="button" type="submit">Add</button>
            </form>
            <ul className="gp-preview">
              {own.slice(0, 6).map((c) => (
                <li key={c.id}>
                  <span>{fmtDate(c.date)} · {c.notes}</span>
                  <span className="numeric">{money(c.amount)}</span>
                </li>
              ))}
              {own.length === 0 && <li className="gp-muted">No contributions yet.</li>}
            </ul>
            <div className="gp-actions">
              <button className="button button--quiet" type="button" onClick={() => setView({ edit: focus.goal.id })}>Edit</button>
              <button className="button button--quiet" type="button" onClick={() => actions.archive(focus.goal.id)}>Archive</button>
              <button className="button button--quiet button--danger" type="button" onClick={() => actions.remove(focus.goal.id)}>Delete</button>
            </div>
          </>
        )}
        {view === "goal" && !focus && <p className="state">No goals yet. Use New to add one.</p>}
      </section>
    </div>
  );
}

export function TileC({ onViewAll }) {
  const { goals, contributions } = useGoals();
  const { money } = useMoney();
  const live = goals
    .filter((g) => !g.past)
    .map((g) => describeGoal(g, contributions))
    .filter((d) => d.status === "Active")
    .sort((a, b) => a.goal.end.localeCompare(b.goal.end));
  return (
    <section className="card gp-tile-c">
      <div className="card__head">
        <h3>Goals</h3>
        <button className="link-button" type="button" onClick={onViewAll}>View all goals</button>
      </div>
      {live.length === 0 ? (
        <p className="state">No active goals yet.</p>
      ) : (
        <div className="gp-tile-c__rings">
          {live.slice(0, 3).map((d) => (
            <div key={d.goal.id} className="gp-tile-c__ring">
              <Ring d={d} size={64} />
              <strong>{d.goal.title}</strong>
              <span className="gp-muted numeric">{money(d.requiredPerMonth)} / mo</span>
              <span className={`gp-dot gp-dot--${d.flag === "Behind" ? "bad" : "good"}`}>{d.flag}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
