// The localisation settings (ADR-0027), loaded once by App and handed down
// through context so every component formats amounts through the same chosen
// Display Currency. Components never build a currency string themselves: they
// take `money` / `preciseMoney` / `signedMoney` from useMoney().

import { createContext, useContext, useMemo } from "react";

import { DEFAULT_CURRENCY_ID } from "./currencies.js";
import * as format from "./format.js";
import { DEFAULT_FINANCIAL_START_MONTH } from "./period.js";

// Each default is owned by the module that interprets it (currencies.js,
// period.js, format.js); this just gathers them into the settings shape.
export const DEFAULT_SETTINGS = {
  currency: DEFAULT_CURRENCY_ID,
  financial_year_start_month: DEFAULT_FINANCIAL_START_MONTH,
  date_order: format.DEFAULT_DATE_ORDER,
};

const SettingsContext = createContext(DEFAULT_SETTINGS);

export function SettingsProvider({ settings, children }) {
  return <SettingsContext.Provider value={settings}>{children}</SettingsContext.Provider>;
}

export function useSettings() {
  return useContext(SettingsContext);
}

// The money helpers bound to the saved Display Currency. Outside a provider
// (a component rendered on its own) they read as the default, Australian dollars.
export function useMoney() {
  const { currency } = useSettings();
  return useMemo(
    () => ({
      money: (value) => format.money(value, currency),
      preciseMoney: (value) => format.preciseMoney(value, currency),
      signedMoney: (value) => format.signedMoney(value, currency),
    }),
    [currency],
  );
}

// The date helpers bound to the saved Date Order (ADR-0027). Month names stay
// English whichever order is chosen.
export function useDateFormat() {
  const { date_order: order } = useSettings();
  return useMemo(
    () => ({
      dayMonth: (isoDate) => format.dayMonth(isoDate, order),
      dayMonthLong: (isoDate) => format.dayMonthLong(isoDate, order),
      generatedAt: (isoDateTime) => format.generatedAt(isoDateTime, order),
    }),
    [order],
  );
}
