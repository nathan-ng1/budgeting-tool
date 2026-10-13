# Cutting a release

Releases are cut manually (ADR-0017). Every release **must** carry the Installation Pack as assets.
`setup.bat`/`setup.command` are downloaded on their own, before a clone exists, so a release
without assets leaves new installs nothing to download.

1. On a `chore/release-X.Y.Z` branch, bump `version` in `pyproject.toml` and add the Version's entry to
   the top of `CHANGELOG.md` (ADR-0029), in the same PR, then merge to `master`. Draft the entry from the
   PRs merged since the last tag (`git log vA.B.C..HEAD --merges`, or `gh pr list --state merged`). The
   heading is `## vX.Y.Z — YYYY-MM-DD` (release date), followed by a flat bullet list of plain-language
   changes a Collaborator would notice, including Installation Pack changes. Leave out release PRs,
   refactors and test-only changes. There is no Unreleased section. A test fails if the newest entry's
   version doesn't match `pyproject.toml`.
2. Tag and publish from `master`, attaching the Installation Pack:

   ```sh
   git switch master && git pull
   gh release create vX.Y.Z --generate-notes \
     windows/setup.bat windows/update.bat docs/setup-guide.html \
     mac/setup.command mac/update.command docs/setup-guide-mac.html
   ```

3. Check that the assets are there:
   `gh release view vX.Y.Z --json assets --jq '.assets[].name'` should list all six files.

To add or replace assets on an existing release:
`gh release upload vX.Y.Z <files…> --clobber`.
