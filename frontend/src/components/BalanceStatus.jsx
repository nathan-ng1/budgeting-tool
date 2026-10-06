import { money, signedMoney } from "../lib/format.js";
import { ADVERSE } from "../lib/tone.js";

// The display rule shared by every "did every dollar get a job?" figure -
// Unallocated on the Overview (#168) and Left to Budget on the Budget tab
// (#167), see GLOSSARY.md and spec #164. Both aim for exactly $0.

// Balanced is exact to the cent (spec #164 has no tolerance band) - this only
// absorbs floating-point dust from summing decimal amounts.
export function isBalanced(value) {
  return Math.abs(value) < 0.005;
}

export function isShort(value) {
  return value < 0 && !isBalanced(value);
}

// The figure as text: signed, except that $0 is neither a surplus nor a
// shortfall so it reads unsigned.
export function balanceText(value) {
  return isBalanced(value) ? money(0) : signedMoney(value);
}

// Adverse only when negative. A positive figure stays neutral rather than
// favourable: the goal is $0, so unassigned money isn't a win.
export function BalanceFigure({ value }) {
  return <span className={`numeric ${isShort(value) ? ADVERSE : ""}`.trim()}>{balanceText(value)}</span>;
}

// Balanced at $0; `shortLabel` when negative ("Over income" for Unallocated,
// "Over-budgeted" for Left to Budget); nothing when positive.
export function BalanceChip({ value, shortLabel }) {
  if (isBalanced(value)) {
    return <span className="status-chip status-chip--positive">Balanced</span>;
  }
  if (value < 0) {
    return <span className="status-chip status-chip--negative">{shortLabel}</span>;
  }
  return null;
}
