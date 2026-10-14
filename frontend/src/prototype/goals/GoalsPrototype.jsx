// PROTOTYPE (issue #209) - throwaway. Three variants of the Goals tab and the Overview Goals
// tile, switched with ?variant=A|B|C on the existing Dashboard route (sub-shape A: mounted in
// the real app, next to the real tabs). All data is in-memory stub data; see store.js.
import "./prototype.css";

import PrototypeSwitcher, { useVariant } from "./PrototypeSwitcher.jsx";
import { TabA, TileA } from "./VariantA.jsx";
import { TabB, TileB } from "./VariantB.jsx";
import { TabC, TileC } from "./VariantC.jsx";

export function GoalsTab() {
  const variant = useVariant();
  return variant === "B" ? <TabB /> : variant === "C" ? <TabC /> : <TabA />;
}

export function GoalsTile({ onViewAll }) {
  const variant = useVariant();
  return variant === "B" ? <TileB onViewAll={onViewAll} /> : variant === "C" ? <TileC onViewAll={onViewAll} /> : <TileA onViewAll={onViewAll} />;
}

export { PrototypeSwitcher };
