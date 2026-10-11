# Localisation settings live in the database, and Display Currency is install-wide and display-only

To make the Dashboard usable outside Australia, three settings become configurable in the Settings
tab: the Display Currency (one dropdown of currencies, each carrying its own symbol position and
separators), the Financial Year start month, and the Date Order (day-first or month-first). All
three are stored in a new settings table in the local database. It is added to the schema the same
additive way as every other table, so no [ADR-0025](./0025-update-runs-pending-migrations-tracked-in-the-database.md)
migration is needed. A setting that has never been saved reads as its default (the Australian
dollar, July, day-first), so current users see no change. The theme
and the Financial Year/Calendar Year choice stay in `localStorage`, because they only change how the
viewer looks at the data and not what the data means.

Currency is deliberately display-only: one per install, no exchange rates or conversion, and no
Transaction carries a currency of its own. Changing it relabels existing amounts. Only currencies
with 0 or 2 decimal places are offered, since the Transaction Log holds every Amount to two
decimals. A Financial Year can begin only on the first of a month, not on an arbitrary day such as the
UK's 6 April. The Dashboard stays English-only: dates keep English month names, and nothing is
translated.

## Considered Options

- **Settings in `localStorage`, like the theme.** Rejected for currency and Financial Year start:
  they change what stored figures mean, so they must survive a cleared browser and travel with a
  database backup. A viewer-only preference like the theme doesn't need that.
- **Per-Transaction currency with exchange rates.** Rejected as a different product (multi-currency
  accounting) that would cut across the Transaction Log, the Date + Amount + Notes dedupe, and every
  total. Adding it later would be a data migration, which is why the decision is recorded.
- **A separate number-format dropdown alongside the currency.** Rejected in favour of one list of
  currencies with predefined conventions, to keep Settings simple.
- **One euro entry per country (Germany, France, Ireland, ...).** Tried first, then collapsed to a
  single "Euro" entry written the German way (1.234,56 €): six near-identical rows made the list
  long for little gain. A euro user who wants another convention is not served; revisit if asked.
- **One Settings card per setting, each with its own Save.** Replaced by a single "Display Settings"
  tile with one Save that sends only the settings that changed, since the three are chosen together
  when setting the Dashboard up for a country.
- **Translated UI text.** Rejected for now: the Dashboard's vocabulary is glossary terms (Available
  to Save, Unallocated, Left to Budget) that are expensive to translate well and to keep translated.
  Revisit if demand appears from a specific language.
- **A day-level Financial Year start, or a week-start-day setting.** Rejected: a start-of-month
  approximation is good enough for budgeting, and a Weekly rule stores a day of the week that doesn't
  depend on where a week begins.

## Consequences

- The Financial Year/Calendar Year switcher ([ADR-0021](./0021-financial-year-switcher-and-calendar-year-toggle.md))
  is hidden when the Financial Year is configured to start in January, as the two framings are then
  identical. The backend already takes a start month (7 or 1), so the change is mostly in the
  frontend's `period.js` and the Budget grid's month order.
- The hand-built `$` strings and the hard-coded `en-AU` grouping in `frontend/src/lib/format.js`
  are replaced by the browser's `Intl.NumberFormat`, driven by the chosen currency.
- Category Budgets are per month ([ADR-0013](./0013-category-budget-is-per-month-across-income-expense-and-debt.md)),
  so moving the Financial Year start changes only how months are grouped, never a stored budget.
- A first-launch walkthrough that confirms these settings belongs to the Retail Edition build, which
  doesn't exist yet. Until then, the Settings tab and the migration defaults are the whole feature.
