import { categoryColours } from "../lib/categoryColours.js";
import { useDateFormat, useMoney } from "../lib/settings.jsx";

// The period's largest single Spending Transactions. `expenses` arrives ranked
// from the backend; `count` is how many rows the period shows. `colourFor` is
// the period's shared Category colour mapping (categoryColours).
export default function TopExpenses({ expenses, count, colourFor = categoryColours([]) }) {
  const { money } = useMoney();
  const { dayMonth } = useDateFormat();
  const rows = expenses.slice(0, count);

  return (
    <section className="card">
      <div className="card__head">
        <h3>Top {count} expenses</h3>
      </div>

      {rows.length === 0 ? (
        <p className="state">No spending recorded for this period.</p>
      ) : (
        <div className="top5">
          {rows.map((expense, index) => (
            <div key={`${index}-${expense.date}-${expense.notes}-${expense.amount}`} className="top5__row">
              <span className="top5__rank numeric">{String(index + 1).padStart(2, "0")}</span>
              <div className="top5__detail">
                <span className="top5__notes" title={expense.notes}>
                  {expense.notes}
                </span>
                <span className="top5__category">
                  <span className="dot dot--sm" style={{ background: colourFor(expense.category) }} />
                  {expense.category}
                </span>
              </div>
              <span className="top5__date">{dayMonth(expense.date)}</span>
              <span className="top5__amount numeric">{money(expense.amount)}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
