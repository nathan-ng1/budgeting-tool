# Retail Edition — design notes (in progress)

Working notes from a `/grill-with-docs` session (2026-10-09) on selling the tool publicly via Etsy
without exposing source. **Paused** while the Collaborator Edition gets more testing and feedback.
Not yet an ADR: once the open questions below are settled, write an ADR superseding
[ADR-0017](./adr/0017-installation-pack-is-a-bootstrapper-distributed-via-releases.md)'s
distribution scope. Terms (Buyer, Collaborator, Retail Edition, Collaborator Edition) are in
`GLOSSARY.md`.

## Settled

| # | Decision |
|---|---|
| Q1 | Make the GitHub repo private. Accept that the code was already public (~248 clones / ~124 uniques, 2–7 Oct 2026; 0 forks). **Not done yet**, waiting on go-ahead (see Q10). |
| Q2 | Source protection level: deterrent. Nuitka-compiled Python + minified frontend JS. |
| Q3 | Retail Edition is Dashboard-only (manual entry, budgets, recurring transactions). No Statement Export pipeline or AI flows. |
| Q4 | Windows and macOS. |
| Q5 | Etsy is the storefront (a firm requirement). Etsy limits: 5 files × 20 MB, so the Etsy download is a PDF containing the download link. Etsy reportedly prohibits subscriptions, so pricing is one-off. Confirm with Etsy Support that standalone software is allowed. |
| Q6 | No piracy protection or license keys. |
| Q7 | Local app (not hosted/SaaS). Dashboard runs on localhost as today, and data never leaves the Buyer's machine (keeps ADR-0008). |
| Q8 | Before the first sale: ABN, EULA (not financial advice / no warranty / limited liability / no redistribution), refund policy (subject to Australian Consumer Law), privacy statement. |
| Q9 | Free updates forever, so hosting and the update channel must be free and durable. |
| Q10 | Making the repo private is safe for Collaborators (nathan-ng1, esthert1455-sudo): `gh auth login` in `setup.bat` covers git and the update check. Non-collaborator clones keep working locally but lose updates. |
| Q11 | Two editions from one codebase. Collaborators stay on the git-based Installation Pack. The Retail Edition build excludes categorisation, sanitising, advisor and budget-suggestion code. |
| Q13 | Buyer data lives in `%LOCALAPPDATA%\BudgetingTool\` / `~/Library/Application Support/BudgetingTool/`, separate from the app. No `.env`: defaults are built in, with a Dashboard settings screen. The Dashboard gets backup/restore. |
| Q14 | First launch: predefined Categories (ADR-0022) plus a short walkthrough (financial year start, recurring income and bills, first budget). |

## Open (round 4, unanswered)

- **Q12′ Hosting:** public GitHub releases-only repo (discoverable) vs **Cloudflare R2 at an
  unguessable path + `latest.json`** (recommended: unlisted, free).
- **Q15′ Install method:** the Mac Gatekeeper/Windows SmartScreen warnings only fire on
  browser-downloaded (quarantined / Mark-of-the-Web) files. Recommended: Mac = Terminal one-liner
  (`curl … | bash`, no quarantine, ad-hoc signature only); Windows = normal `Setup.exe` with the
  "More info → Run anyway" step. Paid Apple signing ($99 USD/yr) is the fallback if Mac refunds or
  support emails pile up. Use Nuitka *standalone* (not onefile) to avoid Defender false positives.
- **Q16 Updates:** recommended: once-a-day automatic check against `latest.json`, manual apply by
  re-running the installer (mirrors ADR-0019).
- **Q17 Migrations:** recommended: the Retail Edition runs pending migrations on launch, with an
  automatic database backup first (Retail counterpart to ADR-0025).

## Selling worldwide (2026-10-11)

A second `/grill-with-docs` session decided the Retail Edition sells worldwide with no tiers and no
price change. Localisation goes in the listing text only, and the price is revisited after tester
feedback. The product side (Display Currency, Financial Year start month, Date Order; English only)
is [ADR-0027](./adr/0027-localisation-settings-are-stored-in-the-database-and-currency-is-display-only.md)
and spec #172. Etsy and tax research, with sources, is in
[research/etsy-selling-rules.md](./research/etsy-selling-rules.md). What it means for open questions:

- **Q5 (software allowed?):** no Etsy policy covers standalone software either way. A PDF linking to
  an external host isn't addressed, and the Services policy bans software/app *membership
  subscriptions*. Still: get a written answer from Etsy Support before listing.
- **Q5 (subscriptions):** only partly confirmed. There is no generic ban, but there is no recurring
  billing feature and software memberships are banned, so one-off pricing stands.
- **Q8 (tax):** Etsy collects and remits VAT/GST on digital downloads for buyers in about 40
  countries, including Australia, plus US sales tax. Whether that relieves an ABN seller of their
  own GST obligation, and whether the ATO's "digital platforms" registration trigger applies, is
  unconfirmed. **Ask a tax agent before the first sale.**
- **Q8 (refunds/ACL):** digital listings can't carry a return policy. Statutory ACL remedies can't
  be excluded by "no refunds" wording, so the refund policy must say so.
- **Shop currency:** list in AUD with an AUD bank account to avoid Etsy's 2.5% conversion fee.
  Buyers in 22 supported currencies see converted prices automatically.

## Revisit after tester feedback

- **Q7 (local install vs no-install browser app):** the user asked whether it can run in the
  browser. Today the Dashboard already *displays* in a browser via a local Python server, but it
  needs an install. A no-install option means either hosted (source hidden, but you hold Buyers'
  financial data and pay recurring hosting) or browser-only (a JS rewrite or Pyodide; data in the
  browser's own storage; the source becomes readable, which undercuts Q2). Ask testers whether the
  install step was a barrier before reopening this.

## Version and Version History (2026-10-13)

A `/grill-with-docs` session on showing the Version under the Dashboard title, with a Version History
link, decided the feature ships in **both** editions. The frontend only asks the backend for its
Version and its history; where those come from is edition-specific. The Collaborator Edition reads
them from the installed package metadata and `CHANGELOG.md`. The Retail Edition can't assume either
(Nuitka build, no clone, and Buyers shouldn't see Collaborator-only items such as the Statement
Export pipeline), so its Version source, its history content, and how that history is shipped with
each release (likely alongside `latest.json`, Q16) are still to be decided here.

## Not yet discussed

- Build pipeline: Nuitka standalone per platform, plus bundled built frontend assets.
- Exactly which modules or code paths get excluded from the Retail build, and how.
- Etsy listing and PDF content checklist; pricing.
