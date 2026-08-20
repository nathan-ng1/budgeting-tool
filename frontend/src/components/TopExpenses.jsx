import { colourForCategory } from "../lib/categoryColours.js";
import { dayMonth, money } from "../lib/format.js";

export default function TopExpenses({ expenses }) {
  return (
    <section className="card">
      <div className="card__head">
        <h3>Top 5 expenses</h3>
      </div>

      {expenses.length === 0 ? (
        <p className="state">No expenses recorded for this month.</p>
      ) : (
        <div className="top5">
          {expenses.map((expense, index) => (
            <div key={`${expense.date}-${expense.notes}-${expense.amount}`} className="top5__row">
              <span className="top5__rank numeric">{String(index + 1).padStart(2, "0")}</span>
              <div className="top5__detail">
                <span className="top5__notes" title={expense.notes}>
                  {expense.notes}
                </span>
                <span className="top5__category">
                  <span className="dot dot--sm" style={{ background: colourForCategory(expense.category) }} />
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
