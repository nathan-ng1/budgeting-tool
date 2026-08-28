# The Installation Pack's non-AI path is Dashboard-only, not a free-tier Ollama install

`setup.bat` asks whether the user holds an AI subscription (Claude Code or Codex CLI) and branches
on the answer. The tempting alternative for "no subscription" was to default them onto the
OpenAI-compatible backend against a local Ollama install — free, no account, still automated
categorisation. We rejected that: `src/categorisation/` has no manual/null backend, so automated
Statement Export processing structurally requires *some* categoriser backend regardless — Ollama
would still mean bundling a model download and local-inference setup into what's supposed to be the
easy, no-subscription path. "Doesn't need AI" instead means the plainest thing it can: Dashboard
only (view/edit transactions, Budget tab, Recurring Transactions Config, manual transaction entry
via the Transactions tab), with the Statement Export pipeline out of scope entirely for that user
until they choose otherwise. Ollama stays a valid, documented option in the README, just not part of
the guided script.

## Consequences

- A Dashboard-only user has no scripted path to automated categorisation; they add transactions by
  hand via the Dashboard's Transactions tab.
- Adding AI later is just re-running `setup.bat` and picking the AI path — no separate upgrade
  flow (see [ADR-0017](./0017-installation-pack-is-a-bootstrapper-distributed-via-releases.md)).
