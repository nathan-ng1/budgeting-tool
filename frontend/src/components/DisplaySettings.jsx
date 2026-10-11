import { useId } from "react";

import { CURRENCIES } from "../lib/currencies.js";
import { preciseMoney } from "../lib/format.js";
import { MONTH_LABELS_LONG } from "../lib/months.js";
import { useSettingsSave } from "../lib/useSettingsSave.js";

// The sample every currency entry shows, so a user can tell which entry
// matches their own conventions before choosing it.
const SAMPLE_AMOUNT = 1234.56;

// The two orders, each with a sample so a user can tell which one they mean.
const ORDERS = [
  { id: "day-first", label: "Day first (19 Aug)" },
  { id: "month-first", label: "Month first (Aug 19)" },
];

// Display Currency, Financial Year start month and Date Order (ADR-0027) in a
// single tile on the Settings tab, saved together with one button that sends
// only what changed. `saved` is the settings payload (currency,
// financial_year_start_month, date_order); `onSaved` hands the server's answer
// (every setting) back to App, which re-renders every amount, month and date.
export default function DisplaySettings({ saved, onSaved }) {
  const currencyNoteId = useId();
  const monthNoteId = useId();
  const orderNoteId = useId();
  const { draft, set, saving, error, save, changeCount } = useSettingsSave(saved, onSaved);

  return (
    <section className="card">
      <h3>Display Settings</h3>
      <div className="settings-grid">
        <div className="settings-grid__item">
          <label className="field">
            <span className="field__label">Display Currency</span>
            <select value={draft.currency} onChange={(event) => set("currency")(event.target.value)} aria-describedby={currencyNoteId}>
              {CURRENCIES.map((entry) => (
                <option key={entry.id} value={entry.id}>
                  {`${entry.code} - ${preciseMoney(SAMPLE_AMOUNT, entry.id)}`}
                </option>
              ))}
            </select>
          </label>
          <p id={currencyNoteId} className="card__note">
            Changing the currency relabels existing amounts and never converts them.
          </p>
        </div>

        <div className="settings-grid__item">
          <label className="field">
            <span className="field__label">Financial Year start month</span>
            <select
              value={draft.financial_year_start_month}
              onChange={(event) => set("financial_year_start_month")(Number(event.target.value))}
              aria-describedby={monthNoteId}
            >
              {MONTH_LABELS_LONG.map((name, index) => (
                <option key={name} value={index + 1}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <p id={monthNoteId} className="card__note">
            Moving the start month regroups your months into a different year. It never changes a Category Budget.
          </p>
        </div>

        <div className="settings-grid__item">
          <label className="field">
            <span className="field__label">Date Order</span>
            <select value={draft.date_order} onChange={(event) => set("date_order")(event.target.value)} aria-describedby={orderNoteId}>
              {ORDERS.map((order) => (
                <option key={order.id} value={order.id}>
                  {order.label}
                </option>
              ))}
            </select>
          </label>
          <p id={orderNoteId} className="card__note">
            Month names are always English.
          </p>
        </div>
      </div>

      {error !== null && (
        <p className="state state--error" role="alert">
          {error}
        </p>
      )}
      <div className="settings-footer">
        <button type="button" className="button" disabled={saving || changeCount === 0} onClick={save}>
          Save settings
        </button>
        {changeCount > 0 && (
          <span className="settings-footer__dirty">
            {changeCount} unsaved change{changeCount > 1 ? "s" : ""}
          </span>
        )}
      </div>
    </section>
  );
}
