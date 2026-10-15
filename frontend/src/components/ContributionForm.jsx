import { useState } from "react";

// The Add contribution form on a Goal card. The backend owns every rule (a
// positive amount, an active Goal), so this only gathers the fields and shows
// whatever the backend says when it refuses them.
export default function ContributionForm({ goal, today, onSave, onCancel }) {
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(today);
  const [notes, setNotes] = useState(goal.title);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await onSave({ amount: Number(amount), date, notes: notes.trim() });
    } catch (cause) {
      setError(cause.message);
      setSaving(false);
    }
  }

  return (
    <form className="rule-form goals__form" onSubmit={submit}>
      <div className="rule-form__grid">
        <label className="field">
          <span className="field__label">Amount</span>
          <input
            type="number"
            min="0.01"
            step="0.01"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
          />
        </label>
        <label className="field">
          <span className="field__label">Date</span>
          <input type="date" value={date} onChange={(event) => setDate(event.target.value)} />
        </label>
        <label className="field field--wide">
          <span className="field__label">Notes</span>
          <input value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
      </div>
      {error !== null && (
        <p className="field__hint field__hint--error" role="alert">
          {error}
        </p>
      )}
      <div className="rule-form__actions">
        <button type="submit" className="button" disabled={saving}>
          Save contribution
        </button>
        <button type="button" className="button button--quiet" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
