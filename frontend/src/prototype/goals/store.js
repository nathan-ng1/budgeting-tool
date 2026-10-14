// PROTOTYPE (issue #209) - throwaway. In-memory store: survives tab switches,
// wiped on reload. Mutations are stubs - nothing reaches the backend.
import { useSyncExternalStore } from "react";

import { addMonthsISO, splitCents, todayISO } from "./goalsMath.js";

let nextId = 100;
const id = () => ++nextId;

function monthly(goalId, startIso, months, amount, notes) {
  return Array.from({ length: months }, (_, i) => ({
    id: id(),
    goalId,
    date: addMonthsISO(startIso, i + 0),
    amount,
    category: "Goals",
    notes,
  }));
}

function seed() {
  const t = todayISO();
  const goals = [
    { id: 1, title: "Japan trip", description: "Two weeks, Tokyo and Kyoto, April cherry blossoms.", target: 8000, start: addMonthsISO(t, -8), end: addMonthsISO(t, 5), past: null },
    { id: 2, title: "Emergency fund", description: "Three months of essentials sitting in the offset.", target: 15000, start: addMonthsISO(t, -10), end: addMonthsISO(t, 14), past: null },
    { id: 3, title: "New laptop", description: "", target: 2400, start: addMonthsISO(t, -6), end: addMonthsISO(t, 2), past: null },
    { id: 4, title: "Car rego & service", description: "Rego, CTP and the 60,000 km service.", target: 1800, start: addMonthsISO(t, -9), end: addMonthsISO(t, -1), past: null },
    { id: 5, title: "House deposit", description: "10% on a two-bed unit. Starts once the car is paid off.", target: 60000, start: addMonthsISO(t, 1), end: addMonthsISO(t, 60), past: null },
    { id: 6, title: "Wedding gift", description: "Cousin's wedding.", target: 500, start: addMonthsISO(t, -12), end: addMonthsISO(t, -7), past: "archived" },
    { id: 7, title: "Road bike", description: "Dropped for now.", target: 400, start: addMonthsISO(t, -5), end: addMonthsISO(t, 1), past: "deleted" },
  ];
  const contributions = [
    ...monthly(1, addMonthsISO(t, -8), 8, 450, "Japan trip"),
    ...monthly(2, addMonthsISO(t, -10), 10, 700, "Emergency fund"),
    ...monthly(3, addMonthsISO(t, -6), 6, 400, "New laptop"),
    ...monthly(4, addMonthsISO(t, -9), 9, 122.22, "Car rego & service"),
    ...monthly(6, addMonthsISO(t, -12), 5, 100, "Wedding gift"),
    ...monthly(7, addMonthsISO(t, -5), 3, 40, "Road bike"),
  ];
  return {
    goals,
    contributions,
    // Stand-in for the selected month's Unallocated on the Overview (decision Q21).
    unallocated: 1240,
    lastPercents: { 1: 40, 2: 30 },
    lastSplit: null,
  };
}

let state = seed();
const listeners = new Set();
const set = (next) => {
  state = next;
  listeners.forEach((l) => l());
};
const subscribe = (l) => {
  listeners.add(l);
  return () => listeners.delete(l);
};

export const useGoals = () => useSyncExternalStore(subscribe, () => state);

const patchGoal = (goalId, patch) =>
  set({ ...state, goals: state.goals.map((g) => (g.id === goalId ? { ...g, ...patch } : g)) });

export const actions = {
  addGoal(fields) {
    set({ ...state, goals: [...state.goals, { id: id(), past: null, ...fields }] });
  },
  updateGoal: (goalId, fields) => patchGoal(goalId, fields),
  archive: (goalId) => patchGoal(goalId, { past: "archived" }),
  remove: (goalId) => patchGoal(goalId, { past: "deleted" }),
  reactivate: (goalId) => patchGoal(goalId, { past: null }),
  addContribution(goalId, { amount, date }) {
    const goal = state.goals.find((g) => g.id === goalId);
    set({
      ...state,
      contributions: [...state.contributions, { id: id(), goalId, date, amount, category: "Goals", notes: goal.title }],
    });
  },
  // percents: { [goalId]: pct }. Writes one Goals-Category row per Goal with a share plus a
  // remainder row in `restCategory` (Savings or Investments).
  applySplit({ total, date, percents, restCategory }) {
    const rows = Object.entries(percents)
      .filter(([, pct]) => pct > 0)
      .map(([key, pct]) => ({ key, pct }));
    const amounts = splitCents(total, rows);
    const written = [];
    for (const { key } of rows) {
      const goal = state.goals.find((g) => g.id === Number(key));
      written.push({ id: id(), goalId: goal.id, date, amount: amounts[key], category: "Goals", notes: goal.title });
    }
    if (amounts.__rest > 0) {
      written.push({ id: id(), goalId: null, date, amount: amounts.__rest, category: restCategory, notes: restCategory });
    }
    set({
      ...state,
      contributions: [...state.contributions, ...written],
      lastPercents: Object.fromEntries(rows.map((r) => [r.key, r.pct])),
      lastSplit: written,
      unallocated: Math.max(state.unallocated - total, 0),
    });
  },
  clearLastSplit: () => set({ ...state, lastSplit: null }),
};
