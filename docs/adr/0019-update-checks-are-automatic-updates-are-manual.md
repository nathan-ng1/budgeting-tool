# Update checks are automatic on Dashboard launch; applying an update stays manual

CONTEXT.md's opening line calls this whole tool "a personal, manually-triggered process," and
[ADR-0008](./0008-dashboard-is-a-local-web-app-not-a-hosted-artifact.md) established that nothing
about the Dashboard page reaches the network so transaction data never leaves the machine. Against
that backdrop, having `open_dashboard.bat` silently call the GitHub Releases API on every launch
needed deliberate justification rather than being the obvious default.

We decided it's a narrower concern than either precedent: the check sends no transaction data and
touches nothing about the Dashboard page itself (ADR-0008's actual guarantee), it's throttled
(roughly once/day) and best-effort/silent if offline or `gh` isn't authenticated, and it only ever
prints a notice ("update available — run update.bat") — it never pulls or applies anything on its
own. Applying an update is a separate, explicit, manually-run step (`update.bat`: fetch tags, show
what changed, confirm, then pull and re-sync deps), preserving the manually-triggered principle for
the part that actually changes the user's install.

## Consequences

- `open_dashboard.bat` gains a dependency on `gh` CLI being installed and authenticated (see
  [ADR-0017](./0017-installation-pack-is-a-bootstrapper-distributed-via-releases.md)) to perform the
  check at all; its absence degrades to no notice, never an error.
- `update.bat` is scoped purely to pull-latest-and-re-sync — it does not handle reconfiguring an
  existing install (e.g. switching AI path), which stays `setup.bat`'s job.
