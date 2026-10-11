import { MONTH_LABELS_LONG } from "../lib/months.js";
import { useSettingSave } from "../lib/useSettingSave.js";

// Financial Year start month (ADR-0027) - a card of its own on the Settings
// tab, saved explicitly like Display Currency. `startMonth` is the saved month
// number (1-12); `onSaved` hands the server's answer (every setting) back to
// App, which regroups the whole Dashboard around it.
export default function FinancialYearStart({ startMonth, onSaved }) {
  const { selected, setSelected, saving, error, save, unchanged } = useSettingSave("financial_year_start_month", startMonth, onSaved);

  return (
    <section className="card">
      <h3>Financial Year</h3>
      <label className="field">
        <span className="field__label">Financial Year start month</span>
        <select value={selected} onChange={(event) => setSelected(Number(event.target.value))}>
          {MONTH_LABELS_LONG.map((name, index) => (
            <option key={name} value={index + 1}>
              {name}
            </option>
          ))}
        </select>
      </label>
      <p className="card__note">
        Moving the start month regroups your months into a different year. It never changes a Category Budget.
      </p>
      {error !== null && (
        <p className="state state--error" role="alert">
          {error}
        </p>
      )}
      <button type="button" className="button" disabled={saving || unchanged} onClick={save}>
        Save Financial Year start
      </button>
    </section>
  );
}
