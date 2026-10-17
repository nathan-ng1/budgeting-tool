# Cutting a release

Releases are cut manually (ADR-0017). Every release **must** carry the Installation Pack as assets.
`setup.bat`/`setup.command` are downloaded on their own, before a clone exists, so a release
without assets leaves new installs nothing to download.

1. On a `chore/release-X.Y.Z` branch, bump `version` in `pyproject.toml` and add the Version's entry to
   the top of `CHANGELOG.md` (ADR-0029), in the same PR, then merge to `master`. Draft the entry from the
   PRs merged since the last tag (`git log vA.B.C..HEAD --merges`, or `gh pr list --state merged`). The
   heading is `## vX.Y.Z — YYYY-MM-DD` (release date), followed by plain-language changes a Collaborator
   would notice, including Installation Pack changes, as bullets under `### New features` and
   `### Bug fixes` sub-headings (leave out a sub-heading with nothing under it). Bullets only
   Collaborators would care about, such as Statement Export pipeline changes, go under a
   `### Collaborator Edition only` sub-heading in the same entry: the Dashboard shows that group
   to Collaborators, and the Retail build leaves it out (step 2). Leave out release PRs,
   refactors and test-only changes. There is no Unreleased section. A test fails if the newest entry's
   version doesn't match the installed package's version (what the Dashboard reports as the running
   Version). That tracks `pyproject.toml` only once the environment is re-synced, so run `uv sync` after
   bumping `version` and before running the tests.
2. For a compiled (Retail) build, write the Version and Version History into the build with
   `python -m dashboard.build_info` (run from the synced environment, so the Version is the one just
   bumped). It writes `src/dashboard/build_info.json` (gitignored) from the installed package's
   version and `CHANGELOG.md`, with every `### Collaborator Edition only` group and any Version left
   empty by that filter removed, and fails rather than write an empty history if the changelog is
   missing or malformed. `--changelog`, `--output` and `--version` override the defaults. When
   that file sits beside the Dashboard, the backend serves the Version and Version History from it
   instead of package metadata and `CHANGELOG.md`. The Collaborator Edition never builds it.
3. Tag and publish from `master`, attaching the Installation Pack:

   ```sh
   git switch master && git pull
   gh release create vX.Y.Z --generate-notes \
     windows/setup.bat windows/update.bat docs/setup-guide.html \
     mac/setup.command mac/update.command docs/setup-guide-mac.html
   ```

4. Check that the assets are there:
   `gh release view vX.Y.Z --json assets --jq '.assets[].name'` should list all six files.

To add or replace assets on an existing release:
`gh release upload vX.Y.Z <files…> --clobber`.

## The Retail Windows build

`.github/workflows/retail-windows-build.yml` compiles the Retail Edition with Nuitka (standalone, not onefile)
and smoke-tests it (Issue #252). It runs when a `vX.Y.Z` tag is pushed, so step 3 above also starts it. It
fails if the tag does not match the Version in `pyproject.toml`. It can also be run by hand from the Actions
tab, and runs on pull requests that touch the build files. The output is a `BudgetingTool-windows` workflow
artifact (a zip of the standalone folder) kept for 14 days; the installer and the upload to the host are separate work.

To build and test it on a Windows machine with the repo's tools (a C compiler is downloaded by Nuitka if
Visual Studio's is not installed), from the repo root:

```sh
uv sync --group retail-build          # adds Nuitka to the environment; a plain `uv sync` removes it again
(cd frontend && npm ci && npm run build)
uv run python -m dashboard.build_info
uv run python -m retail_build build   # compile, then check no Collaborator-only module is in it
uv run python -m retail_build smoke   # launch it and check capabilities, Version, picker and Quit
```

The result is in `retail-build/retail_app.dist/` (git-ignored). The smoke test may open a browser tab.

**Actions minutes.** The repo is public, so Actions are free today. A private repo gets free minutes each month
(2,000 on the Free plan, 3,000 on Pro or Team) and is billed per minute after that, at the standard runner rates
(USD, checked October 2026): Linux $0.006, Windows $0.010, macOS $0.062. GitHub's older docs said Windows minutes
use up the free allowance at 2x and macOS at 10x; the current docs list rates instead and no longer say, so check
the usage on the billing page after the first private run. Eight releases were tagged in the first two weeks of
October 2026; a steady cadence of a few a month is the plan. At roughly 15 minutes a Windows build (an estimate
until a CI run is timed), a build is about $0.15 if billed, so a few a month stay within the free minutes or cost
a dollar or two even at the old 2x. The macOS build (Issue #253) costs about six times as much per minute. Pull
requests only start the build when they touch the build files, so ordinary work costs nothing.
