// PROTOTYPE - throwaway (branch prototype/unallocated-placement). Not for master.
//
// Question: where should Unallocated (Income − every outflow incl. Saved) sit
// on the Overview, next to the renamed Available to Save tile (ex Net
// Balance), and should Left to Budget (the planned counterpart) show beside it?
// Five variants on the existing Overview, switchable via `?variant=A..E`,
// replacing only the StatTiles + IncomeAllocation pair. `?planned=on` adds
// Left to Budget; `?scenario=balanced|over` fakes Saved so you can see the
// $0 and negative states against real data.
import { allocationBar } from "../../lib/allocationBar.js";
import { money, signedMoney } from "../../lib/format.js";
import { toneFor } from "../../lib/tone.js";
import PrototypeSwitcher, { useUrlParam } from "./PrototypeSwitcher.jsx";
import "./prototype.css";

const VARIANTS = [
  { key: "A", name: "Headline on the allocation bar" },
  { key: "B", name: "7th tile" },
  { key: "C", name: "Inside the Saved tile" },
  { key: "D", name: "Equation strip, plan vs actual" },
  { key: "E", name: "Balance check side card" },
];

const TOGGLES = [
  {
    param: "planned",
    label: "Left to Budget",
    options: [
      { key: "off", label: "hidden" },
      { key: "on", label: "shown" },
    ],
  },
  {
    param: "scenario",
    label: "Data",
    options: [
      { key: "real", label: "real" },
      { key: "balanced", label: "fake $0" },
      { key: "over", label: "fake negative" },
    ],
  },
];

const OUTFLOW_TYPES = ["Expense", "Bills & Subscriptions", "Debt", "Savings"];

// --- derived figures -------------------------------------------------------

function withScenario(tiles, scenario) {
  if (scenario === "balanced") return { ...tiles, saved: tiles.net_balance };
  if (scenario === "over") return { ...tiles, saved: Math.max(tiles.net_balance, 0) + 250 };
  return tiles;
}

function allocationFrom(tiles) {
  const income = tiles.income;
  const pct = (amount) => (income > 0 ? (amount / income) * 100 : 0);
  const unallocated = Math.round((tiles.net_balance - tiles.saved) * 100) / 100;
  const remaining = Math.max(unallocated, 0);
  const over = Math.max(-unallocated, 0);
  return {
    expenses_amount: tiles.expenses,
    expenses_pct: pct(tiles.expenses),
    bills_subscriptions_amount: tiles.bills_subscriptions,
    bills_subscriptions_pct: pct(tiles.bills_subscriptions),
    debt_amount: tiles.debt,
    debt_pct: pct(tiles.debt),
    saved_amount: tiles.saved,
    saved_pct: pct(tiles.saved),
    remaining_amount: remaining,
    remaining_pct: pct(remaining),
    over_income_amount: over,
    over_income_pct: pct(over),
  };
}

// Planned figures from Budgeted vs Actual's rows - null when nothing is budgeted.
function plannedFrom(rows) {
  const budgeted = rows.filter((row) => row.budgeted !== null);
  if (budgeted.length === 0) return null;
  const byType = {};
  for (const row of budgeted) byType[row.type] = (byType[row.type] ?? 0) + row.budgeted;
  const income = byType.Income ?? 0;
  const outflows = OUTFLOW_TYPES.reduce((sum, type) => sum + (byType[type] ?? 0), 0);
  return {
    income,
    expenses: byType.Expense ?? 0,
    bills_subscriptions: byType["Bills & Subscriptions"] ?? 0,
    debt: byType.Debt ?? 0,
    saved: byType.Savings ?? 0,
    availableToSave: income - outflows + (byType.Savings ?? 0),
    leftToBudget: income - outflows,
  };
}

const isZero = (value) => Math.abs(value) < 0.005;

// Unallocated's agreed rule (grilling Q6): signed, red when negative, neutral
// when positive, "Balanced" at exactly $0.
function UnallocatedFigure({ value, className = "" }) {
  return (
    <span className={`numeric ${className} ${value < 0 && !isZero(value) ? "figure--adverse" : ""}`}>
      {isZero(value) ? money(0) : signedMoney(value)}
    </span>
  );
}

function BalancedChip({ value }) {
  if (isZero(value)) return <span className="proto-chip proto-chip--good">Balanced</span>;
  if (value < 0) return <span className="proto-chip proto-chip--bad">Over income</span>;
  return null;
}

function AvailableToSaveValue({ value }) {
  return isZero(value) ? money(0) : signedMoney(value);
}

// --- shared pieces (not layouts) --------------------------------------------

function Tile({ label, value, tone, average, children }) {
  return (
    <div className="tile">
      <div className="tile__label">{label}</div>
      <div className={`tile__value numeric ${tone ?? ""}`}>{value}</div>
      {average && <div className="tile__average numeric">{average} / month average</div>}
      {children}
    </div>
  );
}

const SEGMENT_COLOURS = {
  expenses: "var(--color-negative-fill)",
  bills_subscriptions: "var(--color-bills-subscriptions)",
  debt: "var(--color-debt)",
  saved: "var(--color-savings)",
  remaining: "var(--color-accent-2-500)",
  over_income: "var(--color-danger)",
};

function AllocationBar({ allocation, showAmounts = false }) {
  const bar = allocationBar(allocation);
  return (
    <>
      <div className="allocation__legend proto-legend">
        {bar.segments.map((segment) => (
          <span key={segment.key} className="allocation__legend-item">
            <span className="dot dot--lg" style={{ background: SEGMENT_COLOURS[segment.key] }} />
            {segment.key === "remaining" ? "Unallocated" : segment.label}{" "}
            <span className="muted">
              {segment.key === "over_income" || showAmounts ? money(segment.amount) : `${segment.pct.toFixed(1)}%`}
            </span>
          </span>
        ))}
      </div>
      <div className="allocation__bar-wrap">
        <div className="allocation__bar">
          {bar.segments.map((segment) => (
            <div
              key={segment.key}
              className="allocation__segment"
              style={{ width: segment.width, background: SEGMENT_COLOURS[segment.key] }}
            />
          ))}
        </div>
        <div className="allocation__marker" style={{ left: bar.incomeMarkerLeft }} />
      </div>
      <div className="allocation__ticks">
        {bar.ticks.map((tick) => (
          <span key={tick.label} className="allocation__tick numeric" style={{ left: tick.left }}>
            {tick.label}
          </span>
        ))}
      </div>
    </>
  );
}

function FirstFourTiles({ tiles, average }) {
  return (
    <>
      <Tile label="Real Income" value={money(tiles.income)} average={average && money(average.income)} />
      <Tile label="Expenses" value={money(tiles.expenses)} average={average && money(average.expenses)} />
      <Tile
        label="Bills & Subscriptions"
        value={money(tiles.bills_subscriptions)}
        average={average && money(average.bills_subscriptions)}
      />
      <Tile label="Debt" value={money(tiles.debt)} average={average && money(average.debt)} />
    </>
  );
}

function AvailableToSaveTile({ tiles, average }) {
  return (
    <Tile
      label="Available to Save"
      value={<AvailableToSaveValue value={tiles.net_balance} />}
      tone={toneFor(-tiles.net_balance)}
      average={average && money(average.net_balance)}
    />
  );
}

function PlannedNote({ planned }) {
  if (planned === null) return <span className="muted">No Category Budgets set</span>;
  return (
    <span className="muted">
      Left to Budget <UnallocatedFigure value={planned.leftToBudget} />
    </span>
  );
}

// --- A: headline on the allocation bar --------------------------------------

function VariantA({ tiles, average, unallocated, planned, showPlanned, allocation }) {
  return (
    <>
      <div className="tiles">
        <FirstFourTiles tiles={tiles} average={average} />
        <AvailableToSaveTile tiles={tiles} average={average} />
        <Tile label="Saved" value={money(tiles.saved)} average={average && money(average.saved)} />
      </div>
      <section className="card">
        <div className="card__head">
          <h3>Where did my income go?</h3>
          <div className="proto-headline">
            <div className="proto-headline__label">Unallocated</div>
            <div className="proto-headline__value">
              <UnallocatedFigure value={unallocated} /> <BalancedChip value={unallocated} />
            </div>
            {average && (
              <div className="tile__average numeric">{money(average.net_balance - average.saved)} / month average</div>
            )}
            {showPlanned && (
              <div className="proto-headline__note">
                <PlannedNote planned={planned} />
              </div>
            )}
          </div>
        </div>
        <AllocationBar allocation={allocation} />
      </section>
    </>
  );
}

// --- B: 7th tile -------------------------------------------------------------

function VariantB({ tiles, average, unallocated, planned, showPlanned, allocation }) {
  return (
    <>
      <div className="tiles proto-tiles--7">
        <FirstFourTiles tiles={tiles} average={average} />
        <AvailableToSaveTile tiles={tiles} average={average} />
        <Tile label="Saved" value={money(tiles.saved)} average={average && money(average.saved)} />
        <Tile
          label="Unallocated"
          value={<UnallocatedFigure value={unallocated} />}
          average={average && money(average.net_balance - average.saved)}
        >
          <div className="proto-tile-extra">
            <BalancedChip value={unallocated} />
          </div>
          {showPlanned && (
            <div className="tile__average">
              <PlannedNote planned={planned} />
            </div>
          )}
        </Tile>
      </div>
      <section className="card">
        <div className="card__head">
          <h3>Where did my income go?</h3>
        </div>
        <AllocationBar allocation={allocation} />
      </section>
    </>
  );
}

// --- C: inside the Saved tile -------------------------------------------------

function VariantC({ tiles, average, unallocated, planned, showPlanned, allocation }) {
  return (
    <>
      <div className="tiles">
        <FirstFourTiles tiles={tiles} average={average} />
        <AvailableToSaveTile tiles={tiles} average={average} />
        <Tile label="Saved" value={money(tiles.saved)} average={average && money(average.saved)}>
          <div className="proto-saved-split">
            <span className="tile__label">Unallocated</span>
            <span className="proto-saved-split__value">
              <UnallocatedFigure value={unallocated} /> <BalancedChip value={unallocated} />
            </span>
          </div>
          {showPlanned && (
            <div className="tile__average">
              <PlannedNote planned={planned} />
            </div>
          )}
        </Tile>
      </div>
      <section className="card">
        <div className="card__head">
          <h3>Where did my income go?</h3>
        </div>
        <AllocationBar allocation={allocation} />
      </section>
    </>
  );
}

// --- D: equation strip, plan vs actual ---------------------------------------

function VariantD({ tiles, average, unallocated, planned, showPlanned, allocation }) {
  const outflows = tiles.expenses + tiles.bills_subscriptions + tiles.debt;
  const rows = [{ label: "Actual", income: tiles.income, outflows, available: tiles.net_balance, saved: tiles.saved, left: unallocated }];
  if (showPlanned && planned !== null) {
    rows.push({
      label: "Plan",
      income: planned.income,
      outflows: planned.expenses + planned.bills_subscriptions + planned.debt,
      available: planned.availableToSave,
      saved: planned.saved,
      left: planned.leftToBudget,
    });
  }
  return (
    <>
      <div className="tiles proto-tiles--4">
        <FirstFourTiles tiles={tiles} average={average} />
      </div>
      <section className="card proto-equation">
        <div className="card__head">
          <h3>Did every dollar get a job?</h3>
          {showPlanned && planned === null && <span className="muted">No Category Budgets set for a Plan row</span>}
        </div>
        <div className="proto-equation__grid">
          <span />
          <span className="tile__label">Income</span>
          <span className="proto-op">−</span>
          <span className="tile__label">Spent, paid &amp; owed</span>
          <span className="proto-op">=</span>
          <span className="tile__label">Available to Save</span>
          <span className="proto-op">−</span>
          <span className="tile__label">Saved</span>
          <span className="proto-op">=</span>
          <span className="tile__label">{rows.length > 1 ? "Unallocated / Left to Budget" : "Unallocated"}</span>
          {rows.map((row) => (
            <Row key={row.label} row={row} muted={row.label === "Plan"} />
          ))}
        </div>
      </section>
      <section className="card">
        <div className="card__head">
          <h3>Where did my income go?</h3>
        </div>
        <AllocationBar allocation={allocation} />
      </section>
    </>
  );

  function Row({ row, muted }) {
    const cls = `proto-equation__value numeric ${muted ? "proto-equation__value--plan" : ""}`;
    return (
      <>
        <span className="proto-equation__rowlabel">{row.label}</span>
        <span className={cls}>{money(row.income)}</span>
        <span />
        <span className={cls}>{money(row.outflows)}</span>
        <span />
        <span className={`${cls} ${muted ? "" : toneFor(-row.available)}`}>
          <AvailableToSaveValue value={row.available} />
        </span>
        <span />
        <span className={cls}>{money(row.saved)}</span>
        <span />
        <span className={cls}>
          <UnallocatedFigure value={row.left} /> <BalancedChip value={row.left} />
        </span>
      </>
    );
  }
}

// --- E: balance check side card ----------------------------------------------

function VariantE({ tiles, average, unallocated, planned, showPlanned, allocation }) {
  const available = tiles.net_balance;
  const savedShare = available > 0 ? Math.min(tiles.saved / available, 1.5) : 0;
  return (
    <>
      <div className="tiles">
        <FirstFourTiles tiles={tiles} average={average} />
        <AvailableToSaveTile tiles={tiles} average={average} />
        <Tile label="Saved" value={money(tiles.saved)} average={average && money(average.saved)} />
      </div>
      <div className="proto-row-2-1">
        <section className="card">
          <div className="card__head">
            <h3>Where did my income go?</h3>
          </div>
          <AllocationBar allocation={allocation} />
        </section>
        <section className="card proto-balance">
          <div className="tile__label">Unallocated</div>
          <div className="proto-balance__value">
            <UnallocatedFigure value={unallocated} />
            <BalancedChip value={unallocated} />
          </div>
          <div className="proto-meter" aria-hidden="true">
            <div
              className="proto-meter__fill"
              style={{ width: `${Math.min(savedShare, 1) * 100}%`, background: "var(--color-savings)" }}
            />
          </div>
          <p className="card__note">
            Saved {money(tiles.saved)} of {money(Math.max(available, 0))} available to save
            {available > 0 ? ` (${Math.round((tiles.saved / available) * 100)}%)` : ""}.
          </p>
          {showPlanned && (
            <p className="card__note">
              <PlannedNote planned={planned} />
              {planned !== null && ` · planned to save ${money(planned.saved)}`}
            </p>
          )}
        </section>
      </div>
    </>
  );
}

const COMPONENTS = { A: VariantA, B: VariantB, C: VariantC, D: VariantD, E: VariantE };

export default function UnallocatedOverviewPrototype({ overview, average }) {
  const [variant] = useUrlParam("variant", "A");
  const [plannedParam] = useUrlParam("planned", "off");
  const [scenario] = useUrlParam("scenario", "real");

  const tiles = withScenario(overview.stat_tiles, scenario);
  const unallocated = tiles.net_balance - tiles.saved;
  const allocation = scenario === "real" ? overview.income_allocation : allocationFrom(tiles);
  const planned = plannedFrom(overview.budgeted_vs_actual);
  const Variant = COMPONENTS[variant] ?? VariantA;

  return (
    <>
      <Variant
        tiles={tiles}
        average={average}
        unallocated={unallocated}
        planned={planned}
        showPlanned={plannedParam === "on"}
        allocation={allocation}
      />
      <PrototypeSwitcher param="variant" title="Overview" variants={VARIANTS} toggles={TOGGLES} />
    </>
  );
}
