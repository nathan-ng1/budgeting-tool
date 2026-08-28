# macOS gets a mirrored Installation Pack via .command scripts, not a shared cross-platform script

[ADR-0017](./0017-installation-pack-is-a-bootstrapper-distributed-via-releases.md) shipped the
Installation Pack Windows-only. Extending it to macOS (issue #117) meant choosing between two
shapes: a single cross-platform installer (e.g. a Python script both OSes run the same way) or a
second, native script mirroring `windows/setup.bat` feature-for-feature in Bash. We chose the
mirror. This repo's existing convention is thin, untested `.bat` orchestration around a tested
Python seam (`src/setup`) — a cross-platform installer would mean either reimplementing that
orchestration in Python (a new, untested-by-precedent layer) or accepting a Python dependency
before Python itself is guaranteed to exist on a fresh machine, which defeats the point of a
bootstrapper. `mac/*.command` files keep the same shape as `windows/*.bat`: native to their shell,
thin, and shelling out to the same `src/setup` functions.

Because the two operating systems' scripts are no longer visually or structurally interchangeable
(`.bat` vs `.command`, `winget` vs `Homebrew`), they're kept in separate top-level folders —
`windows/` and `mac/` — rather than interleaved at the repo root as `windows/setup.bat` gains a
same-named Windows-only neighbour. `tests/dev/` gained the same split.

A few macOS-specific behaviours don't have a Windows analogue and are resolved as follows:

- **Gatekeeper/quarantine**: a `.command` file downloaded via a browser carries the
  `com.apple.quarantine` extended attribute, so Finder refuses to run it on a plain double-click
  the first time. There's no way to script around this from inside the very file Gatekeeper is
  blocking — `docs/setup-guide-mac.html` documents right-click → Open (or `xattr -d
  com.apple.quarantine`) as a required manual first step, something `docs/setup-guide.html` has no
  equivalent of.
- **Working directory on double-click**: Finder runs a double-clicked `.command` file with the
  shell's cwd set to `$HOME`, not the script's own folder — unlike Windows' `%~dp0`, which is
  reliable regardless of how a `.bat` file was launched. Every `mac/*.command` script resolves its
  own directory explicitly (`SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`) before
  doing anything path-relative.
- **Python provisioning**: `mac/setup.command` does not `brew install python@3.12` — Homebrew's
  Python formula has a long-standing history of PATH/shimming friction. It instead lets `uv sync`
  provision a matching interpreter itself (uv's default managed-Python behaviour), a deliberate
  divergence from Windows' explicit `winget install Python.Python.3.12` step.

## Consequences

- Two Installation Packs now exist in parallel (`windows/` + `docs/setup-guide.html`, `mac/` +
  `docs/setup-guide-mac.html`), both wrapping the same untouched `src/setup` seam from ADR-0017 —
  a behavioural change to `.env` merging or update-availability comparison automatically applies
  to both OSes with no duplicated logic.
- Any future behavioural change to the Installation Pack (a new prerequisite, a new `.env` value)
  needs updating in both `windows/setup.bat` and `mac/setup.command` by hand — there's no shared
  orchestration layer enforcing parity, only convention and this ADR's mirroring intent.
- Linux remains unaddressed; `mac/*.command` is the closer starting point for a future Linux port
  than `windows/*.bat`, given the shared Bash/Homebrew-family tooling, but adapting it (e.g.
  `apt`/`dnf` instead of `brew`, no Gatekeeper step) is deferred.
