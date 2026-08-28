import { currentReferenceYear, periodLabel, referenceYearContaining, storePeriodType } from "../lib/period.js";

// The header row (ADR-0021) that replaces the old static Financial Year
// subtitle - prev/next arrows around a label naming the active year and
// framing, plus a Financial Year/Calendar Year toggle. Rendered once in
// App.jsx, above the nav row, and hidden on the Settings tab, which holds no
// Financial-Year- or Calendar-Year-scoped data.
export default function PeriodSwitcher({
  periodType,
  referenceYear,
  earliestTransactionDate,
  onPeriodTypeChange,
  onReferenceYearChange,
}) {
  const minReferenceYear = earliestTransactionDate
    ? referenceYearContaining(earliestTransactionDate, periodType)
    : null;
  const maxReferenceYear = currentReferenceYear(periodType);

  const canGoBack = minReferenceYear === null || referenceYear > minReferenceYear;
  const canGoForward = referenceYear < maxReferenceYear;

  function selectPeriodType(next) {
    if (next === periodType) {
      return;
    }
    storePeriodType(next);
    onPeriodTypeChange(next);
  }

  return (
    <div className="period-switcher">
      <div className="period-switcher__nav" role="group" aria-label="Select year">
        <button
          type="button"
          className="period-switcher__arrow"
          aria-label="Previous year"
          disabled={!canGoBack}
          onClick={() => onReferenceYearChange(referenceYear - 1)}
        >
          ‹
        </button>
        <span className="period-switcher__label">{periodLabel(referenceYear, periodType)}</span>
        <button
          type="button"
          className="period-switcher__arrow"
          aria-label="Next year"
          disabled={!canGoForward}
          onClick={() => onReferenceYearChange(referenceYear + 1)}
        >
          ›
        </button>
      </div>
      <div className="period-switcher__toggle" role="group" aria-label="Financial Year or Calendar Year">
        <button
          type="button"
          className="period-switcher__toggle-option"
          aria-pressed={periodType === "financial"}
          onClick={() => selectPeriodType("financial")}
        >
          Financial Year
        </button>
        <button
          type="button"
          className="period-switcher__toggle-option"
          aria-pressed={periodType === "calendar"}
          onClick={() => selectPeriodType("calendar")}
        >
          Calendar Year
        </button>
      </div>
    </div>
  );
}
