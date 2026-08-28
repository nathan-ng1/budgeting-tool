import { monthsOfPeriod } from "../lib/period.js";

// `selected` is null for Full year (the 13th pill, alongside the 12 months -
// see ADR-0011) or `{ year, month }` for a specific month. Both the Overview
// and Budget (Issue #64) tabs render every pill, Full year included.
// `periodType` orders the 12 months July-first for a Financial Year,
// January-first for a Calendar Year (ADR-0021).
export default function MonthSelector({ referenceYear, periodType, selected, onSelect }) {
  return (
    <div className="months" role="group" aria-label="Select month">
      <button type="button" className="months__pill" aria-pressed={selected === null} onClick={() => onSelect(null)}>
        Full year
      </button>
      {monthsOfPeriod(referenceYear, periodType).map(({ year, month, label }) => (
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
