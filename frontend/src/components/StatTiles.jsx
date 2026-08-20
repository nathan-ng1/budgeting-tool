import { money, signedMoney } from "../lib/format.js";
import { toneFor } from "../lib/tone.js";

// "Real Income" is the mockup's tile copy for the Income Type - no distinct
// concept, just Income (CONTEXT.md).
export default function StatTiles({ tiles }) {
  const netBalance = tiles.net_balance;

  return (
    <div className="tiles">
      <Tile label="Real Income" value={money(tiles.income)} />
      <Tile label="Expenses" value={money(tiles.expenses)} />
      <Tile
        label="Net Balance"
        // Signed, because which way it went is the point - but an exactly
        // balanced month is neither a surplus nor a shortfall, so it reads
        // as a plain $0. Note the flipped sign against Budgeted vs Actual:
        // there a positive figure is overspend, here it is money left over.
        value={netBalance === 0 ? money(0) : signedMoney(netBalance)}
        tone={toneFor(-netBalance)}
      />
      <Tile label="Transferred" value={money(tiles.transferred)} />
    </div>
  );
}

function Tile({ label, value, tone }) {
  return (
    <div className="tile">
      <div className="tile__label">{label}</div>
      <div className={`tile__value numeric ${tone ?? ""}`}>{value}</div>
    </div>
  );
}
