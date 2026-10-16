import { useEffect, useMemo, useState } from "react";

import BalanceCheck from "./components/BalanceCheck.jsx";
import Budget from "./components/Budget.jsx";
import CategoryManagement from "./components/CategoryManagement.jsx";
import DeleteData from "./components/DeleteData.jsx";
import DisplaySettings from "./components/DisplaySettings.jsx";
import Goals from "./components/Goals.jsx";
import GoalsTile from "./components/GoalsTile.jsx";
import IncomeAllocation from "./components/IncomeAllocation.jsx";
import MonthSelector from "./components/MonthSelector.jsx";
import OverviewDetails, { DEFAULT_SECTION } from "./components/OverviewDetails.jsx";
import PeriodSwitcher from "./components/PeriodSwitcher.jsx";
import QuitApp from "./components/QuitApp.jsx";
import RecurringDuePrompt from "./components/RecurringDuePrompt.jsx";
import RecurringRules from "./components/RecurringRules.jsx";
import SectionHead from "./components/SectionHead.jsx";
import StartupNotice from "./components/StartupNotice.jsx";
import StatTiles from "./components/StatTiles.jsx";
import ThemeSwitcher from "./components/ThemeSwitcher.jsx";
import Transactions from "./components/Transactions.jsx";
import VersionHistory from "./components/VersionHistory.jsx";
import YourData from "./components/YourData.jsx";
import {
  fetchAnnualOverview,
  fetchCapabilities,
  fetchLatestTransactionDate,
  fetchMonthOverview,
  fetchTransactionDateRange,
  fetchVersion,
} from "./lib/api.js";
import { fetchCategories } from "./lib/categoriesApi.js";
import { fetchLauncher } from "./lib/launcherApi.js";
import UpdateBanner from "./components/UpdateBanner.jsx";
import { SPENDING_TYPES, categoryColours } from "./lib/categoryColours.js";
import { DEFAULT_SETTINGS, SettingsProvider, useDateFormat } from "./lib/settings.jsx";
import { fetchSettings } from "./lib/settingsApi.js";
import {
  currentMonth,
  currentReferenceYear,
  effectivePeriodType,
  getStoredPeriodType,
  remapReferenceYear,
} from "./lib/period.js";

// Settings holds the Recurring Transactions Config editor (Issue #29);
// Transactions holds the read-only Transaction list (Issue #33); Budget holds
// the per-month Category Budget editor (Issue #62); Goals holds the savings
// Goals and follows no Financial Year (Goals spec section 10).
const TABS = ["Overview", "Transactions", "Budget", "Goals", "Settings"];
const WIRED_TABS = ["Overview", "Transactions", "Budget", "Goals", "Settings"];

// Loads the localisation settings (ADR-0027) once and hands them to the whole
// Dashboard through context, so every amount is drawn in the saved Display
// Currency. Nothing is drawn until the load settles, so no amount ever flashes
// in a currency that is about to be replaced; a failed load settles on the
// Australian defaults rather than an error banner over figures that are fine.
export default function App() {
  const [settings, setSettings] = useState(null);

  useEffect(() => {
    const controller = new AbortController();

    fetchSettings({ signal: controller.signal })
      .then((loaded) => setSettings({ ...DEFAULT_SETTINGS, ...loaded }))
      .catch((cause) => {
        if (cause.name !== "AbortError") {
          setSettings(DEFAULT_SETTINGS);
        }
      });

    return () => controller.abort();
  }, []);

  if (settings === null) {
    return null;
  }

  return (
    <SettingsProvider settings={settings}>
      <Dashboard settings={settings} onSettingsSaved={setSettings} />
    </SettingsProvider>
  );
}

function Dashboard({ settings, onSettingsSaved }) {
  const { dayMonthLong } = useDateFormat();
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
  // Bumped when recurring transactions are written from the Overview's due
  // prompt (Issue #240), so the figures reload to include them.
  const [overviewRevision, setOverviewRevision] = useState(0);
  // The Breakdown section shown under the Goals (Budget, Spending, ...). Lifted
  // here so it survives a change of month or year, where it would otherwise
  // reset every time the figures reload.
  const [overviewSection, setOverviewSection] = useState(DEFAULT_SECTION);
  const [error, setError] = useState(null);
  // Feeds Spending by Category's legend and Budgeted vs Actual's table
  // (Issue #92) - refetched whenever the Overview is shown: those cards' emoji
  // is cosmetic, so a stale/empty list just means name-only labels, never a
  // page-blocking error.
  const [categories, setCategories] = useState([]);
  // The running Version (ADR-0029), shown under the title, and its Version
  // History. Fetched once; the Version is null until it lands or if it can't be
  // read (the line is then omitted), and the history is null when the changelog
  // is unavailable. `showingHistory` swaps the Version History view in for the
  // tabs. The tab bodies do unmount while it shows (so a tab's own local state,
  // such as the Transactions filters, starts fresh on Back), but the state above
  // lives here and survives: Back lands on the same tab and year/month selection.
  const [version, setVersion] = useState(null);
  const [history, setHistory] = useState(null);
  const [showingHistory, setShowingHistory] = useState(false);
  // Which optional features this build ships (ADR-0033). Null until it
  // lands or if it can't be read, which hides them all: a feature appears only
  // once the backend has said it exists.
  const [capabilities, setCapabilities] = useState(null);
  // Whether the Retail launcher is running this Dashboard (Issue #249): only
  // then are there a startup notice and a Quit. False until it says so.
  const [launcherActive, setLauncherActive] = useState(false);
  // The newer Version the launcher found on its daily check, if any (Issue #251).
  const [availableUpdate, setAvailableUpdate] = useState(null);

  // The Financial Year/Calendar Year switcher's shared state (ADR-0021),
  // consumed by the Overview, Budget, and Transactions tabs below.
  // periodType persists across reloads; referenceYear never does, always
  // starting at the period containing today (ADR-0011's existing
  // no-persistence rule for navigation state).
  // The Financial Year start month is a saved setting (ADR-0027). When it is
  // January the Calendar Year framing is the same year, so the switcher is
  // hidden and Financial Year framing always applies, whatever is stored in
  // the browser - the stored choice itself is left alone.
  const financialStartMonth = settings.financial_year_start_month;
  const [storedPeriodType, setPeriodType] = useState(getStoredPeriodType);
  const periodType = effectivePeriodType(storedPeriodType, financialStartMonth);
  const [referenceYear, setReferenceYear] = useState(() =>
    currentReferenceYear(effectivePeriodType(getStoredPeriodType(), financialStartMonth), new Date(), financialStartMonth),
  );
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

    // Only the Overview reads this list, and Category Management or the
    // Budget tab can change an emoji while it is off screen - so refetch each
    // time it comes back rather than keeping the first copy for the session.
    if (tab !== "Overview") {
      return undefined;
    }

    fetchCategories({ signal: controller.signal })
      .then(setCategories)
      .catch(() => {
        // As above: this only degrades emoji display, so it fails quietly.
      });

    return () => controller.abort();
  }, [tab]);

  useEffect(() => {
    const controller = new AbortController();

    fetchCapabilities({ signal: controller.signal })
      .then((loaded) => setCapabilities(loaded ?? null))
      .catch(() => {
        // Failing closed is the safe degradation: the features just stay hidden.
      });

    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    fetchLauncher({ signal: controller.signal })
      .then((loaded) => {
        setLauncherActive(loaded?.active === true);
        setAvailableUpdate(typeof loaded?.update?.version === "string" ? loaded.update.version : null);
      })
      .catch(() => {
        // Failing closed, as above: no notice and no Quit.
      });

    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    fetchVersion({ signal: controller.signal })
      .then((loaded) => {
        setVersion(loaded?.version ?? null);
        setHistory(loaded?.history ?? null);
      })
      .catch(() => {
        // As above: a missing Version line is a smaller problem than an error
        // banner over a Dashboard that otherwise works.
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
  }, [selected, tab, referenceYear, periodType, overviewRevision]);

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
  // falling back to the period containing today (ADR-0021). The Goals tab shows
  // no switcher at all, so nothing ever asks for its anchor.
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
    setReferenceYear(remapReferenceYear(periodAnchorFor(tab), nextPeriodType, new Date(), financialStartMonth));
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

  // A new start month regroups the months into different years, so none of
  // the year or month selections made under the old one still mean anything:
  // land every tab back on the period containing today.
  function handleSettingsSaved(saved) {
    if (saved.financial_year_start_month !== financialStartMonth) {
      const nextPeriodType = effectivePeriodType(storedPeriodType, saved.financial_year_start_month);
      setReferenceYear(currentReferenceYear(nextPeriodType, new Date(), saved.financial_year_start_month));
      selectPill(null);
      setBudgetSelected(currentMonth());
    }
    onSettingsSaved(saved);
  }

  // One Category colour mapping per Overview period, shared by every card that
  // draws a Category dot so a Category is one colour across the page.
  // Spending Categories the other cards show without any spend this period (an
  // earlier Recurring Charge, a top expense's Category, a budgeted Category)
  // are handed slots too, so they never fall back to a Type grey.
  const colourFor = useMemo(
    () =>
      categoryColours(overview?.spending_by_category ?? [], [
        ...(overview?.recurring_charges?.rows ?? []).map((row) => row.category),
        ...(overview?.top_expenses ?? []).map((row) => row.category),
        ...(overview?.budgeted_vs_actual ?? []).filter((row) => SPENDING_TYPES.includes(row.type)).map((row) => row.category),
      ]),
    [overview],
  );

  // The tab whose body is on screen: none while the Version History view has
  // taken its place, though `tab` itself is kept for Back to Dashboard. The
  // period switcher, the nav and every tab body are all gated on this one value.
  const visibleTab = showingHistory ? null : tab;

  return (
    <div className="page">
      <div className="page__inner">
        <header className="header">
          <div className="header__title">
            <h1>Budgeting Dashboard</h1>
            {version !== null && <p className="header__version">v{version}</p>}
          </div>
          <button type="button" className="link-button" onClick={() => setShowingHistory(true)}>
            Version history
          </button>
        </header>

        <UpdateBanner version={availableUpdate} />
        <StartupNotice active={launcherActive} />

        {showingHistory && (
          <VersionHistory history={history} currentVersion={version} onBack={() => setShowingHistory(false)} />
        )}

        {visibleTab !== null && visibleTab !== "Settings" && visibleTab !== "Goals" && (
          <PeriodSwitcher
            periodType={periodType}
            referenceYear={referenceYear}
            earliestTransactionDate={earliestTransactionDate}
            onPeriodTypeChange={changePeriodType}
            onReferenceYearChange={changeReferenceYear}
          />
        )}

        {visibleTab !== null && (
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
        )}

        {visibleTab === "Settings" && (
          <>
            <ThemeSwitcher />
            <DisplaySettings saved={settings} onSaved={handleSettingsSaved} />
            <CategoryManagement />
            <RecurringRules />
            <YourData />
            <QuitApp active={launcherActive} />
            <DeleteData />
          </>
        )}

        {visibleTab === "Transactions" && <Transactions periodType={periodType} referenceYear={referenceYear} />}

        {visibleTab === "Goals" && <Goals selectedMonth={selected} />}

        {visibleTab === "Budget" && (
          <Budget
            periodType={periodType}
            referenceYear={referenceYear}
            selected={budgetSelected}
            onSelect={setBudgetSelected}
            capabilities={capabilities}
          />
        )}

        {visibleTab === "Overview" && (
          <>
            <RecurringDuePrompt onRun={() => setOverviewRevision((revision) => revision + 1)} />

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
                <div className="row--allocation">
                  <IncomeAllocation allocation={overview.income_allocation} income={overview.stat_tiles.income} />
                  <BalanceCheck
                    tiles={overview.stat_tiles}
                    average={selected === null ? overview.monthly_average : undefined}
                  />
                </div>

                <SectionHead title="Goals" note="Your savings goals and how they are tracking." />
                {/* Goals follow no month or Financial Year (Goals spec section 11), so
                    the tile is the same whichever period the pills select. */}
                <GoalsTile onViewAll={() => setTab("Goals")} />

                <OverviewDetails
                  overview={overview}
                  selected={selected}
                  categories={categories}
                  colourFor={colourFor}
                  section={overviewSection}
                  onSectionChange={setOverviewSection}
                />
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
