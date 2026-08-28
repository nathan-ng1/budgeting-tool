import { useEffect, useState } from "react";

import Budget from "./components/Budget.jsx";
import BudgetedVsActual from "./components/BudgetedVsActual.jsx";
import CategoryManagement from "./components/CategoryManagement.jsx";
import DebtSummary from "./components/DebtSummary.jsx";
import ExpensesOverTime from "./components/ExpensesOverTime.jsx";
import IncomeAllocation from "./components/IncomeAllocation.jsx";
import IncomeVsExpensesByMonth from "./components/IncomeVsExpensesByMonth.jsx";
import MonthByMonth from "./components/MonthByMonth.jsx";
import MonthSelector from "./components/MonthSelector.jsx";
import PeriodSwitcher from "./components/PeriodSwitcher.jsx";
import RecurringRules from "./components/RecurringRules.jsx";
import SpendingByCategory from "./components/SpendingByCategory.jsx";
import StatTiles from "./components/StatTiles.jsx";
import ThemeSwitcher from "./components/ThemeSwitcher.jsx";
import TopExpenses from "./components/TopExpenses.jsx";
import Transactions from "./components/Transactions.jsx";
import { fetchAnnualOverview, fetchLatestTransactionDate, fetchMonthOverview, fetchTransactionDateRange } from "./lib/api.js";
import { fetchCategories } from "./lib/categoriesApi.js";
import { dayMonthLong } from "./lib/format.js";
import { currentMonth, currentReferenceYear, getStoredPeriodType, remapReferenceYear } from "./lib/period.js";

// Settings holds the Recurring Transactions Config editor (Issue #29);
// Transactions holds the read-only Transaction list (Issue #33); Budget holds
// the per-month Category Budget editor (Issue #62).
const TABS = ["Overview", "Transactions", "Budget", "Settings"];
const WIRED_TABS = ["Overview", "Transactions", "Budget", "Settings"];

export default function App() {
  const [tab, setTab] = useState("Overview");
  const [asAt, setAsAt] = useState(null);
  // null = Full year, the Overview tab's default on every load - no
  // persistence of a prior selection (ADR-0011).
  const [selected, setSelected] = useState(null);
  // Budget's own independent pill selection (ADR-0021) - defaults to the
  // current month rather than Full year, unchanged from before Budget was
  // wired to the shared switcher. Lifted here rather than kept as Budget's
  // own local state, for two reasons: a year/framing change made while on
  // the Budget tab needs to anchor or reset it the same way Overview's
  // `selected` above is (see changePeriodType/changeReferenceYear below),
  // and it now survives a tab switch the same way `selected` already does,
  // rather than resetting on every visit as it did when Budget.jsx owned it
  // as local state (Budget.jsx used to unmount on every tab change).
  const [budgetSelected, setBudgetSelected] = useState(currentMonth);
  const [overview, setOverview] = useState(null);
  const [error, setError] = useState(null);
  // Feeds Spending by Category's legend and Budgeted vs Actual's table
  // (Issue #92) - fetched once, the same way `asAt` is: those cards' emoji
  // is cosmetic, so a stale/empty list just means name-only labels, never a
  // page-blocking error.
  const [categories, setCategories] = useState([]);

  // The Financial Year/Calendar Year switcher's shared state (ADR-0021),
  // consumed by the Overview, Budget, and Transactions tabs below.
  // periodType persists across reloads; referenceYear never does, always
  // starting at the period containing today (ADR-0011's existing
  // no-persistence rule for navigation state).
  const [periodType, setPeriodType] = useState(getStoredPeriodType);
  const [referenceYear, setReferenceYear] = useState(() => currentReferenceYear(getStoredPeriodType()));
  // Bounds the switcher's Previous arrow - null (unbounded) until the fetch
  // below resolves, or if it fails.
  const [earliestTransactionDate, setEarliestTransactionDate] = useState(null);

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

    fetchTransactionDateRange({ signal: controller.signal })
      .then(({ earliest }) => setEarliestTransactionDate(earliest))
      .catch(() => {
        // As above: an unbounded Previous arrow is a smaller problem than an
        // error banner, so this failure stays quiet too.
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
        ? fetchAnnualOverview({ year: referenceYear, periodType }, { signal: controller.signal })
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
  }, [selected, tab, referenceYear, periodType]);

  // Full year's and a month's Overview responses are different shapes
  // (Issue #38) - clearing `overview` in the same update as `selected`
  // (rather than only inside the effect above) keeps a render from ever
  // pairing the new selection with the previous, differently-shaped data.
  function selectPill(next) {
    setOverview(null);
    setSelected(next);
  }

  // Transactions has no month/Full-year pill of its own (unlike Overview's
  // `selected`/Budget's `budgetSelected`) - it always anchors like Full year,
  // falling back to the period containing today (ADR-0021).
  function periodAnchorFor(activeTab) {
    if (activeTab === "Budget") {
      return budgetSelected;
    }
    if (activeTab === "Overview") {
      return selected;
    }
    return null;
  }

  // Flipping periodType keeps a selected real month anchored (only its
  // displayed referenceYear/label changes) and falls back Full year to the
  // period containing today (ADR-0021) - see period.js's remapReferenceYear.
  // referenceYear/periodType are shared across tabs, but each tab's own
  // month/Full-year selection isn't (ADR-0021), so the anchor is computed
  // from whichever tab is actually on screen, not always Overview's.
  function changePeriodType(nextPeriodType) {
    setPeriodType(nextPeriodType);
    setReferenceYear(remapReferenceYear(periodAnchorFor(tab), nextPeriodType));
  }

  // Paging to a different year has no "same real month" to preserve the way
  // a periodType flip does - the selected month pill may not even exist in
  // the newly-browsed year's list, so browsing to it lands on Full year
  // instead, the same safe landing spot a periodType flip falls back to.
  // Only the active tab's own selection resets - the other tab's is
  // untouched, since it isn't on screen to need re-anchoring right now.
  // Transactions owns no such selection, so neither branch runs for it.
  function changeReferenceYear(nextReferenceYear) {
    if (tab === "Budget") {
      setBudgetSelected(null);
    } else if (tab === "Overview") {
      selectPill(null);
    }
    setReferenceYear(nextReferenceYear);
  }

  return (
    <div className="page">
      <div className="page__inner">
        <header className="header">
          <h1>Budgeting Dashboard</h1>
        </header>

        {tab !== "Settings" && (
          <PeriodSwitcher
            periodType={periodType}
            referenceYear={referenceYear}
            earliestTransactionDate={earliestTransactionDate}
            onPeriodTypeChange={changePeriodType}
            onReferenceYearChange={changeReferenceYear}
          />
        )}

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
            <CategoryManagement />
            <RecurringRules />
          </>
        )}

        {tab === "Transactions" && <Transactions periodType={periodType} referenceYear={referenceYear} />}

        {tab === "Budget" && (
          <Budget
            periodType={periodType}
            referenceYear={referenceYear}
            selected={budgetSelected}
            onSelect={setBudgetSelected}
          />
        )}

        {tab === "Overview" && (
          <>
            <MonthSelector referenceYear={referenceYear} periodType={periodType} selected={selected} onSelect={selectPill} />

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
              <>
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
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
