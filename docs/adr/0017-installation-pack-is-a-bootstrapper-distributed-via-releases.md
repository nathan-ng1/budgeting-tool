# Installation Pack is a standalone bootstrapper distributed via private-repo GitHub Releases

A new user has nothing installed yet — not even Git — so `setup.bat` can't live only inside the
repo the way `open_dashboard.bat` and friends do; it has to be downloadable and runnable before a
clone exists. We chose to make it a standalone bootstrapper (installs Git via `winget` if missing,
clones the repo, then hands off to per-person setup) and to distribute it — along with `update.bat`
and `docs/setup-guide.html` — as assets attached to tagged GitHub Releases, rather than pointing
new users at raw file links on `master`. Releases give the install/update flow a stable, versioned
anchor instead of tracking a branch that may be mid-change, and set up the same mechanism later used
for update checks (see [ADR-0019](./0019-update-checks-are-automatic-updates-are-manual.md)).

The repo is private, so this is scoped to people explicitly invited as collaborators — not a public
release. Collaborator access grants full source/history visibility with no payment gating, so it
isn't a commercial distribution mechanism; if selling this to strangers becomes a real plan, that's
a separate distribution model to design later; this decision only covers personal/invited-user
distribution.

## Consequences

- `gh` CLI moves from optional (previously only for the issue-tracker skill) to a **required**
  prerequisite for everyone, since an unauthenticated request against a private repo's Releases API
  fails — `setup.bat` installs it via `winget` and runs `gh auth login` if not already authenticated.
- Releases are cut manually (bump `pyproject.toml`'s version, tag `vX.Y.Z`, `gh release create
  --generate-notes`) — no CI. Revisit if the manual cadence becomes a bottleneck.
- `setup.bat` must be idempotent/safely re-runnable — it's also the upgrade path for someone whose
  install predates a Release, and the only path for a Dashboard-only user who later wants to add the
  AI-subscription path (see [ADR-0018](./0018-non-ai-path-is-dashboard-only.md)).
