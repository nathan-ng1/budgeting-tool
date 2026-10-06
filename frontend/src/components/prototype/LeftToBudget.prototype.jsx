// PROTOTYPE - throwaway (branch prototype/unallocated-placement). Not for master.
//
// Question: where should Left to Budget (budgeted Income − every budgeted
// Expense, B&S, Debt and Savings Category) sit on the Budget tab? Three
// variants, switchable via `?budget=A..C`. Each variant renders into one of
// the slots Budget.jsx / BudgetGrid.jsx expose; the others render nothing.
import { money, signedMoney } from "../../lib/format.js";
import PrototypeSwitcher, { useUrlParam } from "./PrototypeSwitcher.jsx";
import "./prototype.css";

const VARIANTS = [
  { key: "A", name: "Footer row under the Type totals" },
  { key: "B", name: "Equation strip above the table" },
  { key: "C", name: "Allocation meter in the card head" },
];

const OUTFLOW_TYPES = ["Expense", "Bills & Subscriptions", "Debt", "Savings"];
const METER_COLOURS = {
  Expense: "var(--color-negative-fill)",
  "Bills & Subscriptions": "var(--color-bills-subscriptions)",
  Debt: "var(--color-debt)",
  Savings: "var(--color-savings)",
};

const isZero = (value) => Math.abs(value) < 0.005;

function split(totals) {
  const income = totals.Income ?? 0;
  const outflows = OUTFLOW_TYPES.reduce((sum, type) => sum + (totals[type] ?? 0), 0);
  return { income, outflows, left: income - outflows };
}

function Figure({ value }) {
  return (
    <span className={`numeric ${value < 0 && !isZero(value) ? "figure--adverse" : ""}`}>
      {isZero(value) ? money(0) : signedMoney(value)}
    </span>
  );
}

function Chip({ value }) {
  if (isZero(value)) return <span className="proto-chip proto-chip--good">Balanced</span>;
  if (value < 0) return <span className="proto-chip proto-chip--bad">Over-budgeted</span>;
  return null;
}

export function BudgetPrototypeSwitcher() {
  return <PrototypeSwitcher param="budget" title="Budget" variants={VARIANTS} />;
}

// slot: "selector" (right of the month pills), "above" (above the editor table), "tfoot" (inside it).
export function LeftToBudgetEditor({ slot, totals }) {
  const [variant] = useUrlParam("budget", "A");
  if (totals === null) return null;
  const { income, outflows, left } = split(totals);

  if (variant === "A" && slot === "tfoot") {
    return (
      <tbody>
        <tr className="budget__total-row proto-left-row">
          <td colSpan={5}>
            Left to Budget <span className="muted proto-small">(Income − everything else)</span> <Chip value={left} />
          </td>
          <td className="table__num">
            <Figure value={left} />
          </td>
        </tr>
      </tbody>
    );
  }

  if (variant === "B" && slot === "above") {
    return (
      <div className="proto-strip">
        <div>
          <div className="tile__label">Budgeted Income</div>
          <div className="proto-strip__value numeric">{money(income)}</div>
        </div>
        <span className="proto-op">−</span>
        <div>
          <div className="tile__label">Budgeted outflows</div>
          <div className="proto-strip__value numeric">{money(outflows)}</div>
          <div className="proto-small muted">Expense, B&amp;S, Debt, Savings</div>
        </div>
        <span className="proto-op">=</span>
        <div>
          <div className="tile__label">Left to Budget</div>
          <div className="proto-strip__value">
            <Figure value={left} /> <Chip value={left} />
          </div>
        </div>
      </div>
    );
  }

  if (variant === "C" && slot === "selector") {
    const axis = Math.max(income, outflows, 1);
    return (
      <div className="proto-head-meter">
        <div className="proto-headline__label">Left to Budget</div>
        <div className="proto-headline__value">
          <Figure value={left} /> <Chip value={left} />
        </div>
        <div className="proto-meter proto-meter--stacked" title="Budgeted outflows against budgeted Income">
          {OUTFLOW_TYPES.map((type) => (
            <div
              key={type}
              style={{ width: `${((totals[type] ?? 0) / axis) * 100}%`, background: METER_COLOURS[type] }}
            />
          ))}
          <div className="proto-meter__marker" style={{ left: `${(income / axis) * 100}%` }} />
        </div>
        <div className="proto-small muted">
          {money(outflows)} of {money(income)} budgeted Income
        </div>
      </div>
    );
  }

  return null;
}

// Full year grid: one extra tbody after the Types. `totals` = gridTotalsByType.
export function LeftToBudgetGrid({ totals }) {
  const [variant] = useUrlParam("budget", "A");
  const months = Object.values(totals)[0]?.length ?? 0;
  const lefts = Array.from({ length: months }, (_, i) =>
    split(Object.fromEntries(Object.entries(totals).map(([type, amounts]) => [type, amounts[i]]))),
  );

  if (variant === "C") {
    return (
      <tbody>
        <tr className="budget__total-row proto-left-row">
          <td>Left to Budget</td>
          {lefts.map(({ income, outflows, left }, i) => {
            if (income === 0 && outflows === 0) return <td key={i} />;
            const share = income > 0 ? Math.min(outflows / income, 1) : outflows > 0 ? 1 : 0;
            return (
              <td key={i} className="table__num">
                <Figure value={left} />
                <div className="proto-meter proto-meter--mini">
                  <div
                    className="proto-meter__fill"
                    style={{
                      width: `${share * 100}%`,
                      background: left < 0 && !isZero(left) ? "var(--color-danger)" : "var(--color-accent-2-500)",
                    }}
                  />
                </div>
              </td>
            );
          })}
        </tr>
      </tbody>
    );
  }

  return (
    <tbody>
      <tr className="budget__total-row proto-left-row">
        <td>Left to Budget</td>
        {lefts.map(({ income, outflows, left }, i) =>
          income === 0 && outflows === 0 ? (
            <td key={i} />
          ) : (
          <td key={i} className="table__num">
            <Figure value={left} />
            {variant === "B" && (
              <div>
                <Chip value={left} />
              </div>
            )}
          </td>
          ),
        )}
      </tr>
    </tbody>
  );
}
