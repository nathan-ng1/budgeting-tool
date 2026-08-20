import { monthsOfFinancialYear } from "../lib/financialYear.js";

export default function MonthSelector({ financialYear, selected, onSelect }) {
  return (
    <div className="months" role="group" aria-label="Select month">
      {monthsOfFinancialYear(financialYear).map(({ year, month, label }) => (
        <button
          key={`${year}-${month}`}
          type="button"
          className="months__pill"
          aria-pressed={year === selected.year && month === selected.month}
          onClick={() => onSelect({ year, month })}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
