// The curated Display Currency list (ADR-0027, GLOSSARY.md). Each entry is an
// ISO 4217 currency code plus the locale whose conventions format it (symbol
// and its position, thousands and decimal separators). One entry per
// currency: the euro is written one way (1.234,56 €) even though countries
// that use it differ, to keep the picker short.
//
// Only 0- and 2-decimal currencies are listed: every Amount is held to two
// decimals, so a 3-decimal dinar could not be shown faithfully.
//
// The `id` is what Settings stores. The server validates a save against its
// own copy of these ids (src/dashboard/settings.py) - keep the two in step.

export const DEFAULT_CURRENCY_ID = "AUD";

export const CURRENCIES = [
  { id: "AUD", code: "AUD", locale: "en-AU" },
  { id: "NZD", code: "NZD", locale: "en-NZ" },
  { id: "USD", code: "USD", locale: "en-US" },
  { id: "CAD", code: "CAD", locale: "en-CA" },
  { id: "GBP", code: "GBP", locale: "en-GB" },
  { id: "EUR", code: "EUR", locale: "de-DE" },
  { id: "CHF", code: "CHF", locale: "de-CH" },
  { id: "SEK", code: "SEK", locale: "sv-SE" },
  { id: "NOK", code: "NOK", locale: "nb-NO" },
  { id: "DKK", code: "DKK", locale: "da-DK" },
  { id: "PLN", code: "PLN", locale: "pl-PL" },
  { id: "CZK", code: "CZK", locale: "cs-CZ" },
  { id: "JPY", code: "JPY", locale: "en-JP" },
  { id: "CNY", code: "CNY", locale: "zh-CN" },
  { id: "KRW", code: "KRW", locale: "ko-KR" },
  { id: "INR", code: "INR", locale: "en-IN" },
  { id: "SGD", code: "SGD", locale: "en-SG" },
  { id: "HKD", code: "HKD", locale: "en-HK" },
  { id: "ZAR", code: "ZAR", locale: "en-ZA" },
  { id: "AED", code: "AED", locale: "en-AE" },
  { id: "BRL", code: "BRL", locale: "pt-BR" },
  { id: "MXN", code: "MXN", locale: "es-MX" },
];

// An unknown or missing id (a setting not loaded yet, or one a newer build
// saved) reads as the default rather than breaking every amount.
export function currencyEntry(id) {
  return CURRENCIES.find((entry) => entry.id === id) ?? CURRENCIES.find((entry) => entry.id === DEFAULT_CURRENCY_ID);
}
