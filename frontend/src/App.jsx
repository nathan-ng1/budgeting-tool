import { useEffect, useState } from "react";

import BudgetedVsActual from "./components/BudgetedVsActual.jsx";
import ExpensesOverTime from "./components/ExpensesOverTime.jsx";
import IncomeAllocation from "./components/IncomeAllocation.jsx";
import MonthSelector from "./components/MonthSelector.jsx";
import RecurringRules from "./components/RecurringRules.jsx";
import SpendingByCategory from "./components/SpendingByCategory.jsx";
import StatTiles from "./components/StatTiles.jsx";
import TopExpenses from "./components/TopExpenses.jsx";
import { fetchMonthOverview } from "./lib/api.js";
import { financialYearFor, financialYearLabel } from "./lib/financialYear.js";
import { dayMonthLong } from "./lib/format.js";

// Transactions and Budget render as the mockup shows them but have no screens
// behind them yet (Issue #28); Settings holds the Recurring Transactions Config
// editor (Issue #29).
const TABS = ["Overview", "Transactions", "Budget", "Settings"];
const WIRED_TABS = ["Overview", "Settings"];

function currentMonth() {
  const today = new Date();
  return { year: today.getFullYear(), month: today.getMonth() + 1 };
}

function todayLabel() {
  const today = new Date();
  const iso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  return dayMonthLong(iso);
}

export default function App() {
  const [tab, setTab] = useState("Overview");
  const [selected, setSelected] = useState(currentMonth);
  const [overview, setOverview] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (tab !== "Overview") {
      return undefined;
    }

    const controller = new AbortController();

    setError(null);
    // Drop the previous month's figures before the new ones land, so the page
    // never shows one month's numbers under another month's selected pill.
    setOverview(null);
    fetchMonthOverview(selected, { signal: controller.signal })
      .then(setOverview)
      .catch((cause) => {
        if (cause.name !== "AbortError") {
          setOverview(null);
          setError(cause.message);
        }
      });

    return () => controller.abort();
  }, [selected, tab]);

  return (
    <div className="page">
      <div className="page__inner">
        <header className="header">
          <div>
            <h1>Budgeting Dashboard</h1>
            <div className="header__subtitle">
              {financialYearLabel(financialYearFor(selected.year, selected.month))}
            </div>
          </div>
        </header>

        <nav className="nav">
          {TABS.map((name) => {
            const className = `nav__tab ${name === tab ? "nav__tab--active" : ""}`;
            const current = name === tab ? "page" : undefined;

            // An unwired tab stays a span rather than a disabled button: it is
            // a label for a screen that doesn't exist yet, not a control that
            // happens to be unavailable.
            return WIRED_TABS.includes(name) ? (
              <button key={name} type="button" className={className} aria-current={current} onClick={() => setTab(name)}>
                {name}
              </button>
            ) : (
              <span key={name} className={className}>
                {name}
              </span>
            );
          })}
          <span className="nav__asat">As at {todayLabel()}</span>
        </nav>

        {tab === "Settings" && <RecurringRules />}

        {tab === "Overview" && (
          <MonthSelector
            financialYear={financialYearFor(selected.year, selected.month)}
            selected={selected}
            onSelect={setSelected}
          />
        )}

        {tab === "Overview" && error !== null && (
          <p className="state state--page state--error" role="alert">
            {error}
          </p>
        )}

        {tab === "Overview" && error === null && overview === null && (
          <p className="state state--page">Loading this month&rsquo;s figures&hellip;</p>
        )}

        {tab === "Overview" && error === null && overview !== null && (
          <>
            <StatTiles tiles={overview.stat_tiles} />
            <IncomeAllocation allocation={overview.income_allocation} income={overview.stat_tiles.income} />

            <div className="row--donut">
              <SpendingByCategory
                spending={overview.spending_by_category}
                total={overview.stat_tiles.expenses}
              />
              <BudgetedVsActual rows={overview.budgeted_vs_actual} />
            </div>

            <div className="row--split">
              <TopExpenses expenses={overview.top_expenses} />
              <ExpensesOverTime overTime={overview.expenses_over_time} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}
