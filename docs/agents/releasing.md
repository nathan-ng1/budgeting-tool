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
