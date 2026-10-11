import { useId } from "react";

import { CURRENCIES } from "../lib/currencies.js";
import { preciseMoney } from "../lib/format.js";
import { useSettingSave } from "../lib/useSettingSave.js";

// The sample every dropdown entry shows, so a user can tell which entry
// matches their own conventions before choosing it.
const SAMPLE_AMOUNT = 1234.56;

// Display Currency (ADR-0027) - a card of its own on the Settings tab, saved
// explicitly. `currency` is the saved entry's id; `onSaved` hands the server's
// answer (every setting) back to App, which re-renders every amount.
export default function DisplayCurrency({ currency, onSaved }) {
  const noteId = useId();
  const { selected, setSelected, saving, error, save, unchanged } = useSettingSave("currency", currency, onSaved);

  return (
    <section className="card">
      <h3>Display Currency</h3>
      <label className="field">
        <span className="field__label">Display Currency</span>
        <select value={selected} onChange={(event) => setSelected(event.target.value)} aria-describedby={noteId}>
          {CURRENCIES.map((entry) => (
            <option key={entry.id} value={entry.id}>
              {`${entry.name} - ${preciseMoney(SAMPLE_AMOUNT, entry.id)}`}
            </option>
          ))}
        </select>
      </label>
      <p id={noteId} className="card__note">
        Changing the currency relabels existing amounts and never converts them.
      </p>
      {error !== null && (
        <p className="state state--error" role="alert">
          {error}
        </p>
      )}
      <button type="button" className="button" disabled={saving || unchanged} onClick={save}>
        Save Display Currency
      </button>
    </section>
  );
}
