import { useCallback, useEffect, useState } from "react";

import { addContribution, archiveGoal, createGoal, deleteGoal, fetchGoals, updateGoal } from "../lib/goalsApi.js";
import { useMoney } from "../lib/settings.jsx";
import GoalCard from "./GoalCard.jsx";
import GoalDetails from "./GoalDetails.jsx";
import GoalForm from "./GoalForm.jsx";
import PastGoals from "./PastGoals.jsx";
import SplitPanel from "./SplitPanel.jsx";

const plural = (count, word) => `${count} ${word}${count === 1 ? "" : "s"}`;

// The Goals tab (Goals spec section 10). It follows no Financial Year: a Goal's
// figures are all-time and measured against the backend's one "today", so this
// takes no period props and draws whatever the Goals endpoint says.
//
// `selectedMonth` ({ year, month }, or null) is the Overview's selected month, used
// only to prefill Split savings from that month's Unallocated; with none selected
// (Full year) the split uses today's month.
export default function Goals({ selectedMonth = null }) {
  const { money } = useMoney();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [splitting, setSplitting] = useState(false);
  // "new", an { edit: id } for the Goal being edited, or null for no form.
  const [panel, setPanel] = useState(null);
  // The id of the Goal whose Details view replaces the grid, or null.
  const [detailId, setDetailId] = useState(null);

  const load = useCallback((signal) => {
    return fetchGoals({ signal })
      .then((loaded) => {
        setError(null);
        setData(loaded);
      })
      .catch((cause) => {
        if (cause.name !== "AbortError") {
          setError(cause.message);
        }
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  if (error !== null) {
    return (
      <p className="state state--page state--error" role="alert">
        {error}
      </p>
    );
  }

  if (data === null) {
    return <p className="state state--page">Loading your goals&hellip;</p>;
  }

  const { goals, past = [], today } = data;
  const savedToGoals = goals.reduce((sum, goal) => sum + goal.saved, 0);
  const activeCount = goals.filter((goal) => goal.status === "Active").length;
  const editing = panel !== null && panel !== "new" ? [...goals, ...past].find((goal) => goal.id === panel.edit) : null;

  // A Goal that has left the list closes its Details view.
  const detail = detailId === null ? null : (goals.find((goal) => goal.id === detailId) ?? null);
  if (detail !== null) {
    return (
      <div className="goals">
        <GoalDetails goal={detail} today={today} onBack={() => setDetailId(null)} />
      </div>
    );
  }

  async function save(fields) {
    if (editing) {
      await updateGoal(editing.id, fields);
    } else {
      await createGoal(fields);
    }
    await load();
    setPanel(null);
  }

  async function moveToPast(goal, move) {
    await move(goal.id);
    await load();
  }

  async function contribute(goal, contribution) {
    await addContribution(goal.id, contribution);
    await load();
  }

  return (
    <div className="goals">
      <section className="card">
        <div className="card__head">
          <div>
            <h3>Goals</h3>
            <div className="goals__muted">
              {plural(activeCount, "active goal")} · {money(savedToGoals)} saved toward goals
            </div>
          </div>
          <div className="goals__actions">
            <button type="button" className="button" onClick={() => setSplitting(true)}>
              Split savings
            </button>
            <button type="button" className="button" onClick={() => setPanel("new")}>
              New goal
            </button>
          </div>
        </div>
      </section>

      {splitting && (
        <SplitPanel
          goals={goals}
          today={today}
          month={selectedMonth ?? { year: Number(today.slice(0, 4)), month: Number(today.slice(5, 7)) }}
          onWritten={load}
          onClose={() => setSplitting(false)}
        />
      )}

      {panel === "new" && <GoalForm today={today} onSave={save} onCancel={() => setPanel(null)} />}
      {editing && <GoalForm key={editing.id} initial={editing} reactivate={editing.state !== "active"} today={today} onSave={save} onCancel={() => setPanel(null)} />}

      {goals.length === 0 ? (
        <p className="state">No goals yet. Add one to start working out what to put aside each month.</p>
      ) : (
        <div className="goals__grid">
          {goals.map((goal) => (
            <GoalCard
              key={goal.id}
              goal={goal}
              today={today}
              onEdit={() => setPanel({ edit: goal.id })}
              onAddContribution={contribute}
              onArchive={() => moveToPast(goal, archiveGoal)}
              onDelete={() => moveToPast(goal, deleteGoal)}
              onDetails={() => setDetailId(goal.id)}
            />
          ))}
        </div>
      )}

      <PastGoals past={past} onReactivate={(goal) => setPanel({ edit: goal.id })} />
    </div>
  );
}
