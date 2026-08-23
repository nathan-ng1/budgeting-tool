import { monthsOfFinancialYear } from "../lib/financialYear.js";

// `selected` is null for Full year (the 13th pill, alongside the 12 months -
// see ADR-0011) or `{ year, month }` for a specific month. `includeFullYear`
// defaults to true (Overview's usage); the Budget tab's basic editor has no
// Full year view yet (Issue #62 - that lands with Issue #64), so it renders
// month pills only.
export default function MonthSelector({ financialYear, selected, onSelect, includeFullYear = true }) {
  return (
    <div className="months" role="group" aria-label="Select month">
      {includeFullYear && (
        <button type="button" className="months__pill" aria-pressed={selected === null} onClick={() => onSelect(null)}>
          Full year
        </button>
      )}
      {monthsOfFinancialYear(financialYear).map(({ year, month, label }) => (
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
