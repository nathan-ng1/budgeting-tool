// PROTOTYPE (issue #209) - throwaway. The add/edit Goal form is deliberately the one thing
// shared across variants (decisions Q9/Q15/Q19); what differs is where it appears.
import { useState } from "react";

import { titleError, todayISO } from "./goalsMath.js";

export default function GoalForm({ goals, initial = null, onSave, onCancel, submitLabel = "Save goal" }) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [target, setTarget] = useState(initial ? String(initial.target) : "");
  const [start, setStart] = useState(initial?.start ?? todayISO());
  const [end, setEnd] = useState(initial?.end ?? "");
  const [error, setError] = useState(null);

  function submit(event) {
    event.preventDefault();
    const problem =
      titleError(goals, title, initial?.id ?? null) ??
      (!(Number(target) > 0) ? "Enter a target amount above zero." : null) ??
      (!end ? "An end date is required - it drives the monthly figure." : null) ??
      (end < start ? "The end date can't be before the start date." : null);
    if (problem) {
      setError(problem);
      return;
    }
    onSave({ title: title.trim(), description: description.trim(), target: Number(target), start, end });
  }

  return (
    <form className="rule-form gp-form" onSubmit={submit}>
      <div className="rule-form__grid">
        <label className="field">
          <span className="field__label">Title</span>
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Japan trip" />
        </label>
        <label className="field">
          <span className="field__label">Target amount</span>
          <input type="number" min="0" step="0.01" value={target} onChange={(e) => setTarget(e.target.value)} />
        </label>
        <label className="field">
          <span className="field__label">Start date</span>
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label className="field">
          <span className="field__label">End date (required)</span>
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </label>
        <label className="field field--wide">
          <span className="field__label">Description (optional)</span>
          <input value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
      </div>
      {error && (
        <p className="field__hint field__hint--error" role="alert">
          {error}
        </p>
      )}
      <div className="rule-form__actions">
        <button type="submit" className="button">
          {submitLabel}
        </button>
        <button type="button" className="button button--quiet" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
