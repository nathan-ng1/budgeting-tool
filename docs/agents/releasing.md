# Cutting a release

Releases are cut manually (ADR-0017). Every release **must** carry the Installation Pack as assets.
`setup.bat`/`setup.command` are downloaded on their own, before a clone exists, so a release
without assets leaves new installs nothing to download.

1. On a `chore/release-X.Y.Z` branch, bump `version` in `pyproject.toml`, then PR and merge to `master`.
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
