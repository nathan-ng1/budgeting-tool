# Retail Edition — design notes (in progress)

Working notes from a `/grill-with-docs` session (2026-10-09) on selling the tool publicly via Etsy
without exposing source. **Paused** while the Collaborator Edition gets more testing and feedback.
The edition seam (decisions S1, S2, S14) is recorded in
[ADR-0033](./adr/0033-the-editions-differ-by-what-ships.md), which supersedes
[ADR-0017](./adr/0017-installation-pack-is-a-bootstrapper-distributed-via-releases.md)'s
distribution scope and partly supersedes ADR-0030. The rest is not yet an ADR. Terms (Buyer,
Collaborator, Retail Edition, Collaborator Edition) are in `GLOSSARY.md`.

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

## Open (round 4; Q12′, Q16, Q17 answered in Round 5 below, Q15′ partly)

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

## Round 5 (2026-10-16): keeping the two editions in sync

A third `/grill-with-docs` session ("what does the current build still need for Retail, and how do we
keep it synced with the Collaborator Edition?"). It answered Q12′, Q16 and Q17 and part of Q15′.

| # | Decision |
|---|---|
| S1 | **Edition is decided by what ships, not a flag or a branch.** Shared code never imports the Collaborator-only packages (`statement_export`, `categorisation`, `sanitising`, `advisor`, `budget_suggestions`, `beem`). The Retail build leaves them out, and the Dashboard asks the backend which capabilities exist (e.g. `/api/edition`). A test enforces the import rule. First work item: the decoupling refactor. `dashboard/server.py` imports `statement_export.pipeline` (recurring "Run now"), `dashboard/queries.py` imports `categorisation.history.normalise_notes`, and `dashboard/budgets.py` + `database/store.py` import `budget_suggestions.suggestion`. Those pieces move into shared modules. |
| S2 | **One data-location resolver for both editions.** Order: `DATABASE_PATH` env var / `.env` override, then a pointer file in the per-user folder, then the default per-user folder. "Change location…" ships in Retail too (it is the Restore path, and lets Buyers keep the Database in Dropbox/OneDrive). It writes `.env` when an override exists, otherwise the pointer file. Collaborators' `.env` keeps working untouched. Partly supersedes ADR-0030. |
| S3 | **One `CHANGELOG.md` for both editions.** Collaborator-only bullets go under their own sub-heading (e.g. `### Collaborator Edition only`). The Retail build filters those out and bakes the Version and history into `build_info.json` (and `latest.json`). The Collaborator Edition still reads `CHANGELOG.md` directly. Answers the open "Version and Version History" question. |
| S4 | **Launcher:** starts the server if it isn't running and opens the browser; a second launch just reopens the running instance; Settings has a **Quit** button. No tray/menu-bar icon, no native window. The console window question is settled in S10. |
| S5 | **Recurring expansion stays manual in both editions**, but the Dashboard shows an "N occurrences are due, run now?" prompt. Auto-run on launch was rejected: a deliberately deleted occurrence would reappear. |
| S6 | **Hosting (Q12′):** Cloudflare R2 at an unguessable path, with `latest.json`. The privacy statement (Q8) must mention that update checks contact it. |
| S7 | **Updates (Q16):** the launcher (not the Dashboard process, keeping ADR-0008's no-network Dashboard) checks `latest.json` at most once a day, silently, failing quietly offline. A Dashboard banner says a new Version is available; applying is manual by re-running the installer (mirrors ADR-0019). |
| S8 | **Migrations (Q17):** the Retail Edition runs pending migrations automatically on launch, after an automatic `pre_migration_backup`. On failure it restores the backup and shows an error. The Collaborator Edition keeps refusing to start until `update` is run. Both share the runner and `pre_migration_backup`; only the *when to run* policy differs. |
| S9 | **Install method (Q15′), partly:** Nuitka *standalone* (not onefile) build. Launch with no paid signing: Mac = Terminal one-liner (run once; the app then opens by double-click), Windows = `Setup.exe` with the SmartScreen "More info → Run anyway" click. The PDF screenshots every step. If more than a few Buyers get stuck, buy Apple signing ($99 USD/yr) first. |
| S10 | **No console window by default**, with a startup notice in the browser page saying the app keeps running in the background and to use Quit in Settings when done. |
| S11 | **Build:** a GitHub Actions workflow builds Windows and Mac on the same `vX.Y.Z` tag as the Collaborator release, from an explicit allowlist of shared packages plus `dashboard` (Collaborator-only packages are never copied in), and uploads installers and `latest.json` to R2. One Version number covers both editions. To check: Actions minutes on a private repo vs release cadence. |
| S12 | **Mac: Apple Silicon only**, macOS 12 or later, stated in the listing. Revisit if Buyers ask for Intel. |
| S13 | **First-run walkthrough is shared by both editions.** It shows only on an empty Database that hasn't completed it, so existing Collaborators never see it. |
| S14 | **Capability-based seam.** The frontend asks `/api/capabilities` (e.g. `{"statement_export": false, "budget_suggestion": false}`) and never checks the edition name. Adding a package to a build later turns its feature on with no frontend change, which keeps a later merge of the editions cheap. The cheap merge is Collaborators moving to the compiled build. Buyers getting the Statement Export pipeline would be a new product: it needs a Dashboard Needs Review flow, a settings screen replacing `.env`, and a position on bring-your-own-AI. |
| S15 | **Per-user install, no admin rights** (Windows `%LOCALAPPDATA%\Programs\BudgetingTool`, Mac `~/Applications`). Uninstalling removes the app only; the data folder stays. |
| S16 | **Port clash:** the launcher picks the next free port and records it so a second launch reopens the right one. The startup notice says to open the app from its icon, not a bookmark. |
| S17 | **Pre-sale testing:** give existing Collaborators the Retail installer from an unlisted R2 path as a pre-release. The gate before listing is the install flow, the walkthrough, and clean Windows and Mac machines, ideally with a tester who has never used the Terminal. |
| S18 | **Business prerequisites** (ABN, EULA, refund policy, privacy statement, tax agent, Etsy Support written answer) are tracked as `ready-for-human` GitHub issues. The legal documents themselves live outside the repo. The repo goes private before the first listing goes live, after confirming the Collaborators' update path works with `gh auth login`. Still needs the user's explicit go-ahead before it runs. |
| S19 | **Q6 stands: no piracy protection or license keys at launch**, plus a cheap kill switch. Keep the R2 path unguessable and out of anything public; the EULA bans redistribution. Watch R2 download counts against Etsy sales. If downloads far exceed sales, rotate the installer path, replace the file in the Etsy listing so past Buyers can re-download, and point `latest.json` at the new path. Etsy gives every Buyer the same static PDF, so per-Buyer links or keys are only possible on another platform, and an in-app license check would break the "data never leaves your machine" promise. |
| S20 | **Etsy stays the plan.** No Plan B platform research for now. The design (R2 hosting, PDF link, `latest.json`) is platform-agnostic, so nothing is built around Etsy specifically. Revisit if Etsy Support says no. A fallback sketch from searches (vendor blogs, unverified): Gumroad / Lemon Squeezy / Paddle as merchants of record, and the Microsoft Store (individual fee dropped, 15% commission) as a Windows complement. |

Gaps found in the current build that Retail still needs (from the code audit): `.env`/repo-root
assumptions in `dashboard/__main__.py`, `database/store.py:resolve_database_path` and `server.py`;
the Budget Suggestion panel, endpoint and table (hide in Retail); Version/history sources
(`importlib.metadata`, repo-root `CHANGELOG.md`); the built `frontend/dist` must be bundled; the
folder picker runs Tk in a child process, so the Nuitka build must bundle Tk and re-launch itself
for it; the first-run walkthrough (Q14) doesn't exist yet.

## Built: the launcher (Issue #249)

`src/launcher/launch.py` (`python -m launcher`). The instance record is `instance.json` (`{"port": n}`) in the
per-user data folder, beside the pointer file. A repeat launch reopens the recorded port if the Dashboard answers
`GET /api/launcher` there with `active: true`; a stale record is discarded. The port scan also treats a taken port
that answers as the app as the running instance, so a double-click right behind the first reuses it rather than
starting a second server. The Dashboard has Quit (`POST /api/quit`) and the startup notice only when the launcher
started it (`build_server(on_quit=...)`); the frontend reads `/api/launcher`, not an edition name. The startup
notice's dismissal is kept in the browser's localStorage, so a launch on a new port shows it again. Not yet done
(other tickets): the daily update check (#251), and running windowless on macOS (#253).

## Built: migrate on launch (Issue #250)

`src/launcher/migrate_on_launch.py`, called by `launch` after the running-instance check (a second launch never
migrates underneath a running Dashboard) and before the Database is opened. It uses the shared runner and
`pre_migration_backup` on a plain connection: nothing pending means no backup; otherwise the backup is made, the
migrations run, and the `.pre-migration-` file stays beside the Database (ADR-0025). A failure copies the backup back
over the Database and removes the copy, so the file is byte-for-byte what it was. A Database recording a migration
this build doesn't know (a newer Version) is refused before anything is written, and so is an unreadable file. Either
way no server starts and no instance is recorded: the launcher writes `startup-error.html` into the data folder and
opens the browser to it, so the next launch simply tries again. The Collaborator startup guard in
`dashboard.__main__` is unchanged.

## Built: the Windows build (Issue #252)

`.github/workflows/retail-windows-build.yml`, which only calls `python -m retail_build` (`src/retail_build/`, tooling
that is not in the build) so a build can be reproduced locally with `uv sync --group retail-build`. It runs on a
`v*` tag, by hand, and on pull requests that touch the build files. Steps: build the frontend, write
`build_info.json`, compile, smoke test, upload `BudgetingTool-windows.zip` as a workflow artifact (the Setup.exe and
the upload to R2 are other tickets).

- **Allowlist.** `retail_build.plan.SHARED_PACKAGES` is passed as `--include-package`; the Collaborator-only packages
  as `--nofollow-import-to`. A test fails if a package appears in `src/` that is in neither list (or the tooling
  list), so a new package is a decision and not a default. After compiling, `bundle_check` reads Nuitka's
  compilation report and fails if any Collaborator-only module was compiled in.
- **Entry point.** `src/retail_app.py` is the one executable (`BudgetingTool.exe`, `--windows-console-mode=disable`).
  It runs the launcher, or the folder picker's process when given `--pick-folder`.
- **Folder picker.** A compiled app has no `python -m`, so it starts itself again with `--pick-folder`. That
  uses `sys.argv[0]`: Nuitka's `sys.executable` is a made-up `...\python.exe` beside the app that does not exist.
  `--enable-plugin=tk-inter` bundles Tcl/Tk. A CI machine cannot answer a dialog, so the smoke test runs
  `BudgetingTool.exe --check-folder-picker`, which starts the picker the way the app does and has it load Tk
  and exit (`--check`) rather than show a dialog. Whether the dialog looks right is checked by hand on a clean machine.
- **Smoke test.** `retail_build.smoke` launches the built app against a throwaway Database and data folder, waits for
  `instance.json`, and fails unless capabilities report every Collaborator-only feature absent, the Version is the one
  being built with no Collaborator-only history, the spreadsheet library works (the import template), the folder
  picker check passes, and Quit stops the app. It also runs in the test suite against a source checkout.
- **Data files.** The built frontend (`dashboard/static`) and `build_info.json` are bundled beside the compiled
  modules, where `Path(__file__)` in `dashboard/server.py` and `build_info.py` already looks.
- **Version.** On a tag the workflow fails unless the tag matches `pyproject.toml`'s version.
- **Actions minutes.** See the note in `docs/agents/releasing.md`.

## Not yet discussed

- Etsy listing and PDF content checklist; pricing.
