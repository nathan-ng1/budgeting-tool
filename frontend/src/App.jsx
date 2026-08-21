import { useEffect, useState } from "react";

import BudgetedVsActual from "./components/BudgetedVsActual.jsx";
import ExpensesOverTime from "./components/ExpensesOverTime.jsx";
import IncomeAllocation from "./components/IncomeAllocation.jsx";
import MonthSelector from "./components/MonthSelector.jsx";
import SpendingByCategory from "./components/SpendingByCategory.jsx";
import StatTiles from "./components/StatTiles.jsx";
import TopExpenses from "./components/TopExpenses.jsx";
import { fetchMonthOverview } from "./lib/api.js";
import { financialYearFor, financialYearLabel } from "./lib/financialYear.js";
import { dayMonthLong } from "./lib/format.js";

// Transactions/Budget/Settings render as the mockup shows them but are not
// wired to real screens yet - Overview is the only tab this round (Issue #28).
const TABS = ["Overview", "Transactions", "Budget", "Settings"];

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
  const [selected, setSelected] = useState(currentMonth);
  const [overview, setOverview] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
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
  }, [selected]);

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
          {TABS.map((tab) => (
            <span
              key={tab}
              className={`nav__tab ${tab === "Overview" ? "nav__tab--active" : ""}`}
              aria-current={tab === "Overview" ? "page" : undefined}
            >
              {tab}
            </span>
          ))}
          <span className="nav__asat">As at {todayLabel()}</span>
        </nav>

        <MonthSelector
          financialYear={financialYearFor(selected.year, selected.month)}
          selected={selected}
          onSelect={setSelected}
        />

        {error !== null && (
          <p className="state state--page state--error" role="alert">
            {error}
          </p>
        )}

        {error === null && overview === null && <p className="state state--page">Loading this month&rsquo;s figures…</p>}

        {error === null && overview !== null && (
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
