# Version History comes from a curated, local CHANGELOG.md, never the network

The Dashboard shows its Version under the title and links to a Version History page of every Version
with its date and a short summary (see `GLOSSARY.md`). The obvious source is GitHub's release notes,
which already exist, but they are raw PR titles, and fetching them at runtime would make the
Dashboard call the network, which [ADR-0008](./0008-dashboard-is-a-local-web-app-not-a-hosted-artifact.md)
and [ADR-0019](./0019-update-checks-are-automatic-updates-are-manual.md) deliberately avoid. So the
Collaborator Edition reads a hand-curated `CHANGELOG.md` at the repo root, written in plain
user-facing language on the `chore/release-X.Y.Z` branch alongside the `pyproject.toml` bump, and the
Dashboard never fetches its history over the network.

The Dashboard's frontend only asks its backend for a Version and a history. Where those come from is
edition-specific: the Collaborator Edition reads installed package metadata and `CHANGELOG.md`, while
the Retail Edition (a compiled build with no clone, whose Buyers shouldn't see Collaborator-only
items) will supply its own source and shipping mechanism. See
[retail-edition-design-notes.md](../retail-edition-design-notes.md).

## Considered Options

- **GitHub release notes fetched at runtime:** nothing to maintain, but breaks offline use and the
  no-network guarantee, and the entries are PR-title noise.
- **GitHub release notes copied into the repo at release time:** works offline, but the entries stay
  PR-title noise rather than a summary a user would read.

## Consequences

- Every release gains a step: write the `CHANGELOG.md` entry from the PRs merged since the last tag,
  in the same PR as the version bump. `docs/agents/releasing.md` carries this step.
- There is no Unreleased section. The newest entry's version always equals the `pyproject.toml`
  version, and a test enforces it so a release can't ship without its entry.
- Entries are `## v<version> — <ISO date>` headings followed by bullets, newest first. From v0.6.0 the
  bullets sit under `### New features` and `### Bug fixes` sub-headings; earlier entries stay flat.
  The backend parses them into `{version, date, entries[], groups[{title, entries[]}]}`, where
  `entries` holds any bullets outside a sub-heading, and the page renders plain text with the group
  titles as headings.
- A missing or malformed `CHANGELOG.md` degrades the page to an "isn't available" message. It never
  breaks the rest of the Dashboard.
- Between releases the Dashboard reports the last released Version, since `pyproject.toml` is only
  bumped when a release is cut.
