import { money } from "../lib/format.js";
import { BalanceChip, BalanceFigure, balanceText } from "./BalanceStatus.jsx";

// The Balance check card beside "Where did my income go?" (#168): Unallocated
// (Income minus every outflow, Savings included - GLOSSARY.md) answers "did
// every dollar get a job?", and the meter shows how much of Available to Save
// actually went to Savings.
//
// `tiles` / `average` are the Overview's stat tiles and (Full year only) the
// backend's per-month average, the same shapes StatTiles takes.
export default function BalanceCheck({ tiles, average }) {
  const available = tiles.available_to_save;
  // With nothing available to save there is no share to show - the meter
  // stays empty and the caption drops its percentage.
  const share = available > 0 ? tiles.saved / available : null;

  return (
    <section className="card balance-check" aria-label="Balance check">
      <div className="tile__label">Unallocated</div>
      <div className="balance-check__value">
        <BalanceFigure value={tiles.unallocated} />
        <BalanceChip value={tiles.unallocated} shortLabel="Over income" />
      </div>
      {average && (
        <div className="tile__average numeric">{balanceText(average.unallocated)} / month average</div>
      )}
      <div className="balance-check__meter" aria-hidden="true">
        <div className="balance-check__fill" style={{ width: `${Math.min(share ?? 0, 1) * 100}%` }} />
      </div>
      <p className="card__note">
        Saved {money(tiles.saved)} of {money(Math.max(available, 0))} available to save
        {share !== null && ` (${Math.round(share * 100)}%)`}
      </p>
    </section>
  );
}
