# The editions differ by what ships, not by a flag or a branch

> Supersedes the distribution scope of [ADR-0017](./0017-installation-pack-is-a-bootstrapper-distributed-via-releases.md)
> and partly supersedes [ADR-0030](./0030-database-location-is-chosen-in-settings-stored-in-env-and-switched-live.md).

The tool is sold to the public as a second, Dashboard-only product, the Retail Edition, alongside
the Collaborator Edition that Collaborators run from a clone. ADR-0017 scoped distribution to people
invited to the private repo and left "selling this to strangers" as a separate model to design
later; this is that design. The aim is that a feature built once reaches both editions, so the
editions must differ in as little as possible.

We decided the editions differ only by **what ships**:

- The **Retail Edition** is the shared core: the Dashboard and everything it needs, compiled.
- The **Collaborator Edition** is the same core plus the Collaborator-only packages
  (`statement_export`, `categorisation`, `sanitising`, `advisor`, `budget_suggestions`, `beem`),
  run from a clone as today.
- **Shared code never imports a Collaborator-only package.** A test enforces it. The Dashboard
  pieces that used to reach into those packages (recurring-rule expansion, the note-normalising
  helper, the Budget Suggestion stored value) live in shared modules.
- **The Dashboard asks the backend which capabilities exist** (`/api/capabilities`, e.g.
  `{"statement_export": false, "budget_suggestion": false}`) and shows or hides features to match.
  The frontend never checks an edition name, so adding a package to a build later turns its feature
  on with no frontend change.
- **There is one data-location resolver** for both editions
  ([ADR-0032](./0032-one-data-location-resolver-with-a-pointer-file.md)): override, then pointer
  file, then the per-user default.
- **The Retail build is an explicit allowlist of packages**: the shared packages plus `dashboard`.
  A Collaborator-only package is never copied in by omission, so adding one to the repo cannot leak
  it into a sale. A smoke test launches the built app and reads its capabilities.

Where the editions genuinely differ in behaviour, the difference is a policy over shared machinery
rather than a fork of it. For example, the migration runner and `pre_migration_backup` are shared;
only *when to run* differs (Retail runs pending migrations on launch, Collaborators keep the
ADR-0025 rule of running them in `update`).

## Considered Options

- **A runtime edition flag** (an env var or config key checked in the code). Rejected. Every
  Collaborator-only import would still ship in the compiled build, so a flag keeps the source in a
  product meant to hide it, and a flag-checking branch is exactly the kind of thing that drifts
  between editions.
- **A long-lived Retail branch.** Rejected. Every Dashboard feature would have to be merged across
  by hand and the branches would diverge, which defeats "built once, reaches both". It also makes
  one Version number across the two editions a coordination chore instead of a property.
- **Two data-location mechanisms** (`.env` for Collaborators, a separate per-user scheme for
  Retail). Rejected. This is the disagreeing-sources-of-truth problem ADR-0030 worried about, and it
  would put the fork inside the Database lookup that every script and the Dashboard depend on. One
  resolver, with `.env` as its highest-priority override, leaves Collaborator installs untouched.
- **A denylist build** (copy everything, exclude the Collaborator-only packages). Rejected in favour
  of the allowlist, because a denylist fails open when a new package is added.
- **Checking the edition name in the frontend.** Rejected in favour of capabilities. Merging the
  editions later (Collaborators moving to the compiled build) would otherwise mean finding and
  rewriting every name check.

## Consequences

- ADR-0017's "personal/invited-user distribution only" no longer holds. The Installation Pack and
  GitHub Releases remain the Collaborator Edition's channel; the Retail Edition is distributed
  separately and is built from the same `vX.Y.Z` tag, so one Version covers both.
- ADR-0030's rule that the location is always stored in the repo-root `.env`, and its rejection of a
  pointer file, are superseded by the shared resolver. Its live switch, move and migrate behaviour
  stand.
- A Collaborator-only feature now has two parts: the package, and a capability that reports it. A
  new Dashboard feature built on a Collaborator-only package must go through a capability, never an
  import.
- The Budget Suggestion table exists in every Database, but is unused when the capability is absent.
- Buyers getting the Statement Export pipeline would be a new product, not a build flag: it would
  need a Dashboard Needs Review flow, a settings screen in place of `.env`, and a position on
  bring-your-own-AI.
- Decisions S1, S2 and S14 in `docs/retail-edition-design-notes.md` are the record of the
  discussion behind this ADR.
