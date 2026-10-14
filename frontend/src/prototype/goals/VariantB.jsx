// PROTOTYPE (issue #209) - throwaway. Variant B "Ledger, split inline": one dense table, one
// row per Goal; the split tool is not a separate form but a "% of new savings" column that
// appears in the same table. Rows expand in place for detail and actions.
import { Fragment, useState } from "react";

import { useMoney } from "../../lib/settings.jsx";
import GoalForm from "./GoalForm.jsx";
import { byStatus, describeGoal, fmtDate, todayISO } from "./goalsMath.js";
import { actions, useGoals } from "./store.js";
import useSplit from "./useSplit.js";

function MiniBar({ d }) {
  return (
    <div className="gp-bar gp-bar--thin">
      <div className={`gp-bar__fill gp-bar__fill--${d.flag === "Behind" ? "behind" : "ok"}`} style={{ width: `${d.fraction * 100}%` }} />
      {d.status === "Active" && <div className="gp-bar__pace" style={{ left: `${d.paceFraction * 100}%` }} />}
    </div>
  );
}

function Flag({ flag }) {
  const tone = { "On track": "good", Behind: "bad", Achieved: "good", Ended: "bad" }[flag] ?? "muted";
  return <span className={`gp-dot gp-dot--${tone}`}>{flag}</span>;
}

function Detail({ d, contributions, onEdit }) {
  const { money } = useMoney();
  const [amount, setAmount] = useState("");
  const rows = contributions.filter((c) => c.goalId === d.goal.id).sort((a, b) => b.date.localeCompare(a.date));
  return (
    <div className="gp-detail-b">
      <div>
        {d.goal.description && <p>{d.goal.description}</p>}
        <p className="gp-muted">
          {fmtDate(d.goal.start)} → {fmtDate(d.goal.end)} · Original plan {money(d.originalPlan)} / month · Even-pace mark today:{" "}
          {money(d.paceAmount)}
        </p>
        <form
          className="gp-inline"
          onSubmit={(e) => {
            e.preventDefault();
            if (Number(amount) > 0) {
              actions.addContribution(d.goal.id, { amount: Number(amount), date: todayISO() });
              setAmount("");
            }
          }}
        >
          <input aria-label="Contribution amount" type="number" step="0.01" min="0" placeholder="Add contribution (today)" value={amount} onChange={(e) => setAmount(e.target.value)} />
          <button className="button" type="submit">Add</button>
        </form>
        <div className="gp-actions">
          <button className="button button--quiet" type="button" onClick={onEdit}>Edit</button>
          <button className="button button--quiet" type="button" onClick={() => actions.archive(d.goal.id)}>Archive</button>
          <button className="button button--quiet button--danger" type="button" onClick={() => actions.remove(d.goal.id)}>Delete</button>
        </div>
      </div>
      <div>
        <div className="gp-muted">Contributions</div>
        <ul className="gp-preview">
          {rows.slice(0, 5).map((c) => (
            <li key={c.id}>
              <span>{fmtDate(c.date)}</span>
              <span className="numeric">{money(c.amount)}</span>
            </li>
          ))}
          {rows.length === 0 && <li className="gp-muted">None yet</li>}
        </ul>
      </div>
    </div>
  );
}

export function TabB() {
  const { goals, contributions, lastSplit } = useGoals();
  const { money } = useMoney();
  const [open, setOpen] = useState(null);
  const [form, setForm] = useState(null); // "new" | { edit, reactivate }
  const [allocating, setAllocating] = useState(false);
  const [showPast, setShowPast] = useState(false);

  const live = goals.filter((g) => !g.past).map((g) => describeGoal(g, contributions)).sort(byStatus);
  const past = goals.filter((g) => g.past);
  const active = live.filter((d) => d.status === "Active").map((d) => d.goal);
  const s = useSplit(active);
  const editing = form?.edit ? goals.find((g) => g.id === form.edit) : null;
  const cols = allocating ? 7 : 6;

  return (
    <section className="card gp gp-b">
      <div className="card__head">
        <h3>Goals</h3>
        <div className="gp-actions">
          <button className="button button--quiet" type="button" aria-pressed={allocating} onClick={() => setAllocating((v) => !v)}>
            {allocating ? "Hide allocation" : "Allocate savings"}
          </button>
          <button className="button" type="button" onClick={() => setForm("new")}>New goal</button>
        </div>
      </div>

      {lastSplit && (
        <p className="state state--page" role="status">
          Wrote {lastSplit.length} transactions.{" "}
          <button className="link-button" type="button" onClick={actions.clearLastSplit}>Dismiss</button>
        </p>
      )}
      {form === "new" && <GoalForm goals={goals} onCancel={() => setForm(null)} onSave={(f) => { actions.addGoal(f); setForm(null); }} />}
      {editing && (
        <GoalForm
          goals={goals}
          initial={editing}
          submitLabel={form.reactivate ? "Reactivate goal" : "Save goal"}
          onCancel={() => setForm(null)}
          onSave={(f) => {
            actions.updateGoal(editing.id, f);
            if (form.reactivate) actions.reactivate(editing.id);
            setForm(null);
          }}
        />
      )}

      <div className="gp-scroll">
        <table className="gp-table">
          <thead>
            <tr>
              <th>Goal</th>
              <th className="gp-r">Saved</th>
              <th className="gp-r">Target</th>
              <th>Progress</th>
              <th className="gp-r">Needs / month</th>
              <th>Status</th>
              {allocating && <th className="gp-r">% of new savings</th>}
            </tr>
          </thead>
          <tbody>
            {live.map((d) => (
              <Fragment key={d.goal.id}>
                <tr className="gp-table__row" onClick={() => setOpen(open === d.goal.id ? null : d.goal.id)} aria-expanded={open === d.goal.id}>
                  <td>
                    <button type="button" className="gp-rowbtn">{d.goal.title}</button>
                  </td>
                  <td className="gp-r numeric">{money(d.saved)}</td>
                  <td className="gp-r numeric">{money(d.goal.target)}</td>
                  <td className="gp-progress">
                    <MiniBar d={d} />
                    <span className="numeric gp-muted">{Math.round((d.saved / d.goal.target) * 100)}%</span>
                  </td>
                  <td className="gp-r numeric">{d.requiredPerMonth === null ? "—" : money(d.requiredPerMonth)}</td>
                  <td><Flag flag={d.flag} /></td>
                  {allocating && (
                    <td className="gp-r" onClick={(e) => e.stopPropagation()}>
                      {d.status === "Active" ? (
                        <span className="gp-pct">
                          <input aria-label={`Percent to ${d.goal.title}`} type="number" min="0" max="100" value={s.percentOf(d.goal.id)} onChange={(e) => s.setPercent(d.goal.id, e.target.value)} />%
                        </span>
                      ) : (
                        <span className="gp-muted">—</span>
                      )}
                    </td>
                  )}
                </tr>
                {open === d.goal.id && (
                  <tr>
                    <td colSpan={cols}>
                      <Detail d={d} contributions={contributions} onEdit={() => setForm({ edit: d.goal.id })} />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {allocating && (
              <tr className="gp-table__rest">
                <td colSpan={cols - 1}>
                  Everything else saved as{" "}
                  <select value={s.restCategory} onChange={(e) => s.setRestCategory(e.target.value)} aria-label="Remainder Category">
                    <option>Savings</option>
                    <option>Investments</option>
                  </select>
                </td>
                <td className="gp-r numeric">{s.restPct.toFixed(0)}%</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {allocating && (
        <div className="gp-allocbar">
          <label className="field">
            <span className="field__label">Total to allocate</span>
            <input type="number" step="0.01" min="0" value={s.total} onChange={(e) => s.setTotal(e.target.value)} />
          </label>
          <label className="field">
            <span className="field__label">Date</span>
            <input type="date" value={s.date} onChange={(e) => s.setDate(e.target.value)} />
          </label>
          <button className="button button--quiet" type="button" onClick={() => s.setTotal(String(s.unallocated))}>
            Unallocated {money(s.unallocated)}
          </button>
          <span className={`numeric ${s.overCap ? "gp-bad" : "gp-muted"}`}>{s.used}% of 100% assigned</span>
          <button className="button" type="button" disabled={!s.canApply} onClick={() => { s.apply(); setAllocating(false); }}>
            Write {s.preview ? s.preview.goals.length + (s.preview.rest.amount > 0 ? 1 : 0) : 0} transactions
          </button>
        </div>
      )}

      <div className="gp-pastbar">
        <button className="link-button" type="button" onClick={() => setShowPast((v) => !v)}>
          {showPast ? "Hide" : "Show"} past goals ({past.length})
        </button>
      </div>
      {showPast && (
        <table className="gp-table gp-table--past">
          <tbody>
            {past.map((g) => (
              <tr key={g.id}>
                <td>{g.title}</td>
                <td><span className="gp-dot gp-dot--muted">{g.past === "archived" ? "Archived" : "Deleted"}</span></td>
                <td className="gp-r numeric">{money(g.target)}</td>
                <td className="gp-r">
                  <button className="button button--quiet" type="button" onClick={() => setForm({ edit: g.id, reactivate: true })}>Reactivate</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

export function TileB({ onViewAll }) {
  const { goals, contributions } = useGoals();
  const { money } = useMoney();
  const live = goals
    .filter((g) => !g.past)
    .map((g) => describeGoal(g, contributions))
    .filter((d) => d.status === "Active")
    .sort((a, b) => a.goal.end.localeCompare(b.goal.end));
  return (
    <section className="card gp-tile-b">
      <div className="card__head">
        <h3>Goals</h3>
        <button className="link-button" type="button" onClick={onViewAll}>View all goals</button>
      </div>
      <table className="gp-table gp-table--tile">
        <tbody>
          {live.slice(0, 3).map((d) => (
            <tr key={d.goal.id}>
              <td>{d.goal.title}</td>
              <td className="gp-r numeric">
                {money(d.saved)} / {money(d.goal.target)}
              </td>
              <td className="gp-r numeric">{Math.round(d.fraction * 100)}%</td>
              <td><Flag flag={d.flag} /></td>
            </tr>
          ))}
          {live.length === 0 && (
            <tr>
              <td className="gp-muted">No active goals yet.</td>
            </tr>
          )}
        </tbody>
      </table>
    </section>
  );
}
