import { Fragment, useEffect, useState } from "react";

import Budget from "./components/Budget.jsx";
import BudgetedVsActual from "./components/BudgetedVsActual.jsx";
import CategoryManagement from "./components/CategoryManagement.jsx";
import DebtSummary from "./components/DebtSummary.jsx";
import ExpensesOverTime from "./components/ExpensesOverTime.jsx";
import IncomeAllocation from "./components/IncomeAllocation.jsx";
import IncomeVsExpensesByMonth from "./components/IncomeVsExpensesByMonth.jsx";
import MonthByMonth from "./components/MonthByMonth.jsx";
import MonthSelector from "./components/MonthSelector.jsx";
// PROTOTYPE (Midnight dark theme), dev-only - see the component's header
// comment. Remove this import and its mount below once the Midnight
// question is settled.
import MidnightThemeProto, { THEME_CHANGE_EVENT } from "./components/MidnightThemeProto.jsx";
import RecurringRules from "./components/RecurringRules.jsx";
import SpendingByCategory from "./components/SpendingByCategory.jsx";
import StatTiles from "./components/StatTiles.jsx";
import ThemeSwitcher from "./components/ThemeSwitcher.jsx";
import TopExpenses from "./components/TopExpenses.jsx";
import Transactions from "./components/Transactions.jsx";
import { fetchAnnualOverview, fetchLatestTransactionDate, fetchMonthOverview } from "./lib/api.js";
import { fetchCategories } from "./lib/categoriesApi.js";
import { financialYearFor, financialYearLabel } from "./lib/financialYear.js";
import { dayMonthLong } from "./lib/format.js";

// Settings holds the Recurring Transactions Config editor (Issue #29);
// Transactions holds the read-only Transaction list (Issue #33); Budget holds
// the per-month Category Budget editor (Issue #62).
const TABS = ["Overview", "Transactions", "Budget", "Settings"];
const WIRED_TABS = ["Overview", "Transactions", "Budget", "Settings"];

function currentMonth() {
  const today = new Date();
  return { year: today.getFullYear(), month: today.getMonth() + 1 };
}

function currentFinancialYear() {
  const { year, month } = currentMonth();
  return financialYearFor(year, month);
}

export default function App() {
  const [tab, setTab] = useState("Overview");
  const [asAt, setAsAt] = useState(null);
  // null = Full year, the Overview tab's default on every load - no
  // persistence of a prior selection (ADR-0011).
  const [selected, setSelected] = useState(null);
  const [overview, setOverview] = useState(null);
  const [error, setError] = useState(null);
  // Feeds Spending by Category's legend and Budgeted vs Actual's table
  // (Issue #92) - fetched once, the same way `asAt` is: those cards' emoji
  // is cosmetic, so a stale/empty list just means name-only labels, never a
  // page-blocking error.
  const [categories, setCategories] = useState([]);
  // PROTOTYPE (Midnight dark theme) - MidnightThemeProto's preview toggle
  // mutates data-theme directly (bypassing React state), which leaves
  // already-rendered theme-coloured elements (e.g. Spending by Category's
  // donut/legend) frozen on whichever theme was active at their last real
  // render. Bumping this on THEME_CHANGE_EVENT and keying the overview
  // content on it forces a remount so those colours get recomputed. Remove
  // alongside MidnightThemeProto once the Midnight question is settled.
  const [themeTick, setThemeTick] = useState(0);

  useEffect(() => {
    if (!import.meta.env.DEV) {
      return undefined;
    }

    function bump() {
      setThemeTick((tick) => tick + 1);
    }

    window.addEventListener(THEME_CHANGE_EVENT, bump);
    return () => window.removeEventListener(THEME_CHANGE_EVENT, bump);
  }, []);

  // There is no Financial Year switcher (ADR-0011): the selector, the header,
  // and Full year all always show the FY containing today.
  const financialYear = currentFinancialYear();

  // Fetched once: the newest Transaction in the log doesn't change as the
  // reader moves between months or tabs.
  useEffect(() => {
    const controller = new AbortController();

    fetchLatestTransactionDate({ signal: controller.signal })
      .then(setAsAt)
      .catch(() => {
        // An undated header is a smaller problem than an error banner over a
        // page whose figures are all fine, so this failure stays quiet.
        setAsAt(null);
      });

    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    fetchCategories({ signal: controller.signal })
      .then(setCategories)
      .catch(() => {
        // As above: this only degrades emoji display, so it fails quietly.
      });

    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (tab !== "Overview") {
      return undefined;
    }

    const controller = new AbortController();

    setError(null);
    // Drop the previous selection's figures before the new ones land, so the
    // page never shows one month's (or Full year's) numbers under another
    // selected pill.
    setOverview(null);
    const request =
      selected === null
        ? fetchAnnualOverview(financialYear, { signal: controller.signal })
        : fetchMonthOverview(selected, { signal: controller.signal });
    request
      .then(setOverview)
      .catch((cause) => {
        if (cause.name !== "AbortError") {
          setOverview(null);
          setError(cause.message);
        }
      });

    return () => controller.abort();
  }, [selected, tab, financialYear]);

  // Full year's and a month's Overview responses are different shapes
  // (Issue #38) - clearing `overview` in the same update as `selected`
  // (rather than only inside the effect above) keeps a render from ever
  // pairing the new selection with the previous, differently-shaped data.
  function selectPill(next) {
    setOverview(null);
    setSelected(next);
  }

  return (
    <div className="page">
      {import.meta.env.DEV && <MidnightThemeProto />}
      <div className="page__inner">
        <header className="header">
          <div>
            <h1>Budgeting Dashboard</h1>
            <div className="header__subtitle">{financialYearLabel(financialYear)}</div>
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
          {asAt !== null && <span className="nav__asat">As at {dayMonthLong(asAt)}</span>}
        </nav>

        {tab === "Settings" && (
          <>
            <ThemeSwitcher />
            <div className="settings-group">
              <CategoryManagement />
              <RecurringRules />
            </div>
          </>
        )}

        {tab === "Transactions" && <Transactions />}

        {tab === "Budget" && <Budget />}

        {tab === "Overview" && (
          <>
            <MonthSelector financialYear={financialYear} selected={selected} onSelect={selectPill} />

            {error !== null && (
              <p className="state state--page state--error" role="alert">
                {error}
              </p>
            )}

            {error === null && overview === null && (
              <p className="state state--page">
                Loading {selected === null ? "the Full year’s" : "this month’s"} figures&hellip;
              </p>
            )}

            {error === null && overview !== null && (
              <Fragment key={themeTick}>
                <StatTiles tiles={overview.stat_tiles} average={selected === null ? overview.monthly_average : undefined} />
                <IncomeAllocation allocation={overview.income_allocation} income={overview.stat_tiles.income} />

                {selected !== null ? (
                  <>
                    <div className="row--wide-pair">
                      <div className="row--wide-pair__top">
                        <SpendingByCategory
                          spending={overview.spending_by_category}
                          total={overview.stat_tiles.expenses}
                          categories={categories}
                        />
                      </div>
                      <div className="row--wide-pair__wide">
                        <BudgetedVsActual rows={overview.budgeted_vs_actual} categories={categories} />
                      </div>
                      <div className="row--wide-pair__bottom">
                        <DebtSummary debtSummary={overview.debt_summary} total={overview.stat_tiles.debt} />
                      </div>
                    </div>
                    <div className="row--split">
                      <TopExpenses expenses={overview.top_expenses} count={5} />
                      <ExpensesOverTime overTime={overview.expenses_over_time} />
                    </div>
                  </>
                ) : (
                  // Full year pairs Month by Month with Budgeted vs Actual
                  // rather than with the donut: over a whole Financial Year
                  // the month-by-month shape is what the donut begs the
                  // reader to ask about (ADR-0011), so Spending by Category
                  // moves down to pair with Top expenses instead.
                  <>
                    <IncomeVsExpensesByMonth months={overview.income_vs_expenses_by_month} />
                    <div className="row--wide-pair">
                      <div className="row--wide-pair__top">
                        <MonthByMonth months={overview.month_by_month} />
                      </div>
                      <div className="row--wide-pair__wide">
                        <BudgetedVsActual rows={overview.budgeted_vs_actual} categories={categories} />
                      </div>
                      <div className="row--wide-pair__bottom">
                        <DebtSummary
                          debtSummary={overview.debt_summary}
                          total={overview.stat_tiles.debt}
                          average={overview.monthly_average.debt}
                        />
                      </div>
                    </div>
                    <div className="row--split">
                      <SpendingByCategory
                        spending={overview.spending_by_category}
                        total={overview.stat_tiles.expenses}
                        categories={categories}
                      />
                      <TopExpenses expenses={overview.top_expenses} count={10} />
                    </div>
                  </>
                )}
              </Fragment>
            )}
          </>
        )}
      </div>
    </div>
  );
}
