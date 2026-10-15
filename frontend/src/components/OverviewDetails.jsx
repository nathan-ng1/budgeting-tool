import BudgetedVsActual from "./BudgetedVsActual.jsx";
import DebtSummary from "./DebtSummary.jsx";
import IncomeVsExpensesByMonth from "./IncomeVsExpensesByMonth.jsx";
import MonthByMonth from "./MonthByMonth.jsx";
import Movers from "./Movers.jsx";
import OutflowsBreakdown from "./OutflowsBreakdown.jsx";
import OutflowsByMonth from "./OutflowsByMonth.jsx";
import RecurringCharges from "./RecurringCharges.jsx";
import SectionHead from "./SectionHead.jsx";
import SegmentedControl from "./SegmentedControl.jsx";
import SpendingByCategory from "./SpendingByCategory.jsx";
import SpendingOverTime from "./SpendingOverTime.jsx";
import TopMerchants from "./TopMerchants.jsx";

export const DEFAULT_SECTION = "budget";

// The Overview's Breakdown: every card below the Goals, one section at a time so
// the page never shows more than one topic's worth. A month and Full year offer
// the same sections with the same cards in each - Full year's counterparts
// (Outflows by month for Outflows breakdown, ten merchants for five) - plus a
// Month by month section that only a whole year has.
//
// `section` is the section shown and `onSectionChange` changes it; both live in
// the parent so the choice survives a move between months. A section the
// selected period doesn't have (Month by month, on a month) falls back to Budget.
export default function OverviewDetails({ overview, selected, categories, colourFor, section, onSectionChange }) {
  const fullYear = selected === null;
  const tiles = overview.stat_tiles;
  const spendingTotal = tiles.expenses + tiles.bills_subscriptions;

  const sections = [
    ...(fullYear
      ? [
          {
            key: "month-by-month",
            title: "Month by month",
            body: (
              <>
                <IncomeVsExpensesByMonth months={overview.income_vs_expenses_by_month} />
                <MonthByMonth months={overview.month_by_month} />
              </>
            ),
          },
        ]
      : []),
    {
      key: "budget",
      title: "Budgeted vs Actual",
      body: <BudgetedVsActual rows={overview.budgeted_vs_actual} categories={categories} colourFor={colourFor} />,
    },
    {
      key: "spending",
      title: "Spending",
      body: (
        <>
          <div className="row--split">
            <SpendingByCategory
              spending={overview.spending_by_category}
              total={spendingTotal}
              categories={categories}
              colourFor={colourFor}
            />
            <TopMerchants merchants={overview.top_merchants} count={fullYear ? 10 : 5} colourFor={colourFor} />
          </div>
          {fullYear ? (
            <OutflowsByMonth months={overview.outflows_by_month} />
          ) : (
            <>
              <OutflowsBreakdown tiles={tiles} />
              <div className="row--split">
                <SpendingOverTime overTime={overview.spending_over_time} />
                <Movers movers={overview.movers} />
              </div>
            </>
          )}
        </>
      ),
    },
    {
      key: "debt",
      title: "Debt",
      body: (
        <DebtSummary
          debtSummary={overview.debt_summary}
          total={tiles.debt}
          average={fullYear ? overview.monthly_average.debt : undefined}
        />
      ),
    },
    {
      key: "bills-subscriptions",
      title: "Bills & Subscriptions",
      body: <RecurringCharges recurring={overview.recurring_charges} colourFor={colourFor} />,
    },
  ];

  const current = sections.find((candidate) => candidate.key === section) ?? sections.find((candidate) => candidate.key === DEFAULT_SECTION);

  return (
    <>
      <SectionHead title="Breakdown" note="One topic at a time. Pick a section for the full detail.">
        <SegmentedControl
          label="Overview section"
          options={sections.map((candidate) => [candidate.key, candidate.title])}
          value={current.key}
          onChange={onSectionChange}
        />
      </SectionHead>
      <div className="section-stack">{current.body}</div>
    </>
  );
}
