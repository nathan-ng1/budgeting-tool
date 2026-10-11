import { monthsOfPeriod } from "../lib/period.js";
import { useSettings } from "../lib/settings.jsx";

// `selected` is null for Full year (the 13th pill, alongside the 12 months -
// see ADR-0011) or `{ year, month }` for a specific month. Both the Overview
// and Budget (Issue #64) tabs render every pill, Full year included.
// `periodType` orders the 12 months from the saved Financial Year start month
// (July by default) for a Financial Year, January-first for a Calendar Year
// (ADR-0021, ADR-0027).
export default function MonthSelector({ referenceYear, periodType, selected, onSelect }) {
  const { financial_year_start_month: financialStartMonth } = useSettings();

  return (
    <div className="months" role="group" aria-label="Select month">
      <button type="button" className="months__pill" aria-pressed={selected === null} onClick={() => onSelect(null)}>
        Full year
      </button>
      {monthsOfPeriod(referenceYear, periodType, financialStartMonth).map(({ year, month, label }) => (
        <button
          key={`${year}-${month}`}
          type="button"
          className="months__pill"
          aria-pressed={selected !== null && year === selected.year && month === selected.month}
          onClick={() => onSelect({ year, month })}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
