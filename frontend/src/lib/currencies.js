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
  { id: "AUD", code: "AUD", locale: "en-AU", name: "Australian dollar" },
  { id: "NZD", code: "NZD", locale: "en-NZ", name: "New Zealand dollar" },
  { id: "USD", code: "USD", locale: "en-US", name: "US dollar" },
  { id: "CAD", code: "CAD", locale: "en-CA", name: "Canadian dollar" },
  { id: "GBP", code: "GBP", locale: "en-GB", name: "British pound" },
  { id: "EUR", code: "EUR", locale: "de-DE", name: "Euro" },
  { id: "CHF", code: "CHF", locale: "de-CH", name: "Swiss franc" },
  { id: "SEK", code: "SEK", locale: "sv-SE", name: "Swedish krona" },
  { id: "NOK", code: "NOK", locale: "nb-NO", name: "Norwegian krone" },
  { id: "DKK", code: "DKK", locale: "da-DK", name: "Danish krone" },
  { id: "PLN", code: "PLN", locale: "pl-PL", name: "Polish zloty" },
  { id: "CZK", code: "CZK", locale: "cs-CZ", name: "Czech koruna" },
  { id: "JPY", code: "JPY", locale: "en-JP", name: "Japanese yen" },
  { id: "CNY", code: "CNY", locale: "zh-CN", name: "Chinese yuan" },
  { id: "KRW", code: "KRW", locale: "ko-KR", name: "South Korean won" },
  { id: "INR", code: "INR", locale: "en-IN", name: "Indian rupee" },
  { id: "SGD", code: "SGD", locale: "en-SG", name: "Singapore dollar" },
  { id: "HKD", code: "HKD", locale: "en-HK", name: "Hong Kong dollar" },
  { id: "ZAR", code: "ZAR", locale: "en-ZA", name: "South African rand" },
  { id: "AED", code: "AED", locale: "en-AE", name: "UAE dirham" },
  { id: "BRL", code: "BRL", locale: "pt-BR", name: "Brazilian real" },
  { id: "MXN", code: "MXN", locale: "es-MX", name: "Mexican peso" },
];

// An unknown or missing id (a setting not loaded yet, or one a newer build
// saved) reads as the default rather than breaking every amount.
export function currencyEntry(id) {
  return CURRENCIES.find((entry) => entry.id === id) ?? CURRENCIES.find((entry) => entry.id === DEFAULT_CURRENCY_ID);
}
