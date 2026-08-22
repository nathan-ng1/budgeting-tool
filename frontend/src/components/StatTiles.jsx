import { money, signedMoney } from "../lib/format.js";
import { toneFor } from "../lib/tone.js";

// "Real Income" is the mockup's tile copy for the Income Type - no distinct
// concept, just Income (CONTEXT.md).
//
// `average` is the Full year view's per-month figures (same StatTiles shape,
// already divided by elapsed months by the backend - see ADR-0011). It is
// omitted for the per-month Overview, where a monthly average makes no sense.
export default function StatTiles({ tiles, average }) {
  const netBalance = tiles.net_balance;

  return (
    <div className="tiles">
      <Tile label="Real Income" value={money(tiles.income)} average={average && money(average.income)} />
      <Tile label="Expenses" value={money(tiles.expenses)} average={average && money(average.expenses)} />
      <Tile label="Debt" value={money(tiles.debt)} average={average && money(average.debt)} />
      <Tile
        label="Net Balance"
        // Signed, because which way it went is the point - but an exactly
        // balanced month is neither a surplus nor a shortfall, so it reads
        // as a plain $0. Note the flipped sign against Budgeted vs Actual:
        // there a positive figure is overspend, here it is money left over.
        value={netBalance === 0 ? money(0) : signedMoney(netBalance)}
        tone={toneFor(-netBalance)}
        average={average && money(average.net_balance)}
        averageNote={average && "excludes transfers"}
      />
      <Tile label="Transferred" value={money(tiles.transferred)} average={average && money(average.transferred)} />
    </div>
  );
}

function Tile({ label, value, tone, average, averageNote }) {
  return (
    <div className="tile">
      <div className="tile__label">{label}</div>
      <div className={`tile__value numeric ${tone ?? ""}`}>{value}</div>
      {average && (
        <div className="tile__average numeric">
          {average} / month{averageNote ? ` · ${averageNote}` : " average"}
        </div>
      )}
    </div>
  );
}
