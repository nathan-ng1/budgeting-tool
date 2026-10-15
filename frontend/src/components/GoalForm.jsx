import { useState } from "react";

// The add/edit Goal form. The backend owns every rule (a unique title, a target
// above zero, an end date no earlier than the start), so this only gathers the
// fields and shows whatever the backend says when it refuses them.
// `reactivate` is set when editing a Past goal: saving also returns it to
// active (Goals spec section 7.1).
export default function GoalForm({ initial = null, reactivate = false, today, onSave, onCancel }) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [target, setTarget] = useState(initial ? String(initial.target_amount) : "");
  const [start, setStart] = useState(initial?.start_date ?? today);
  const [end, setEnd] = useState(initial?.end_date ?? "");
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await onSave({
        title: title.trim(),
        description: description.trim() || null,
        target_amount: Number(target),
        start_date: start,
        end_date: end,
        ...(reactivate ? { state: "active" } : {}),
      });
    } catch (cause) {
      setError(cause.message);
      setSaving(false);
    }
  }

  return (
    <form className="rule-form goals__form" onSubmit={submit}>
      <div className="rule-form__grid">
        <label className="field">
          <span className="field__label">Title</span>
          <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Japan trip" />
        </label>
        <label className="field">
          <span className="field__label">Target amount</span>
          <input
            type="number"
            min="0"
            step="0.01"
            value={target}
            onChange={(event) => setTarget(event.target.value)}
          />
        </label>
        <label className="field">
          <span className="field__label">Start date</span>
          <input type="date" value={start} onChange={(event) => setStart(event.target.value)} />
        </label>
        <label className="field">
          <span className="field__label">End date (required)</span>
          <input type="date" value={end} onChange={(event) => setEnd(event.target.value)} />
        </label>
        <label className="field field--wide">
          <span className="field__label">Description (optional)</span>
          <input value={description} onChange={(event) => setDescription(event.target.value)} />
        </label>
      </div>
      {error !== null && (
        <p className="field__hint field__hint--error" role="alert">
          {error}
        </p>
      )}
      <div className="rule-form__actions">
        <button type="submit" className="button" disabled={saving}>
          Save goal
        </button>
        <button type="button" className="button button--quiet" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
