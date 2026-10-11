import { useSettingSave } from "../lib/useSettingSave.js";

// The two orders, each with a sample so a user can tell which one they mean.
const ORDERS = [
  { id: "day-first", label: "Day first (19 Aug)" },
  { id: "month-first", label: "Month first (Aug 19)" },
];

// Date Order (ADR-0027) - a card of its own on the Settings tab, saved
// explicitly. `dateOrder` is the saved order; `onSaved` hands the server's
// answer (every setting) back to App, which re-renders every date.
export default function DateOrder({ dateOrder, onSaved }) {
  const { selected, setSelected, saving, error, save, unchanged } = useSettingSave("date_order", dateOrder, onSaved);

  return (
    <section className="card">
      <h3>Date Order</h3>
      <label className="field">
        <span className="field__label">Date Order</span>
        <select value={selected} onChange={(event) => setSelected(event.target.value)}>
          {ORDERS.map((order) => (
            <option key={order.id} value={order.id}>
              {order.label}
            </option>
          ))}
        </select>
      </label>
      {error !== null && (
        <p className="state state--error" role="alert">
          {error}
        </p>
      )}
      <button type="button" className="button" disabled={saving || unchanged} onClick={save}>
        Save Date Order
      </button>
    </section>
  );
}
