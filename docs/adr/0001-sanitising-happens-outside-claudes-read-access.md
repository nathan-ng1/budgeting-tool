# Sanitising happens in a Python script, outside Claude's read access

Unsanitised Statement Exports land in the Transactions Inbox (`D:\natha\Documents\Transactions`), a location outside the project directory that Claude never reads. A Python script — not Claude — performs issuer-specific sanitising (which may be a no-op, as for ANZ) and moves the result into `.data\`, the only location Claude is allowed to read from.

We chose a deterministic script over letting Claude read and cleanse the raw file directly, even though Claude is capable of that, so that personal information can never enter Claude's context even transiently — the guarantee holds regardless of issuer or prompt, rather than depending on Claude reliably self-censoring on every run.
