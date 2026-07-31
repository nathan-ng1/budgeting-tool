# Recurring schedule expansion happens in a deterministic script, not Claude

The Recurring Transactions Config stores schedules as structured columns (Frequency, Interval, Day, Start Date, End Date) rather than free-text rules, and a script — not Claude — expands them into actual dated occurrences using a standard recurrence library.

We considered letting Claude read a human-readable rule (e.g. "every 2 weeks on Wed starting 2026-08-05") and work out which dates fall due each run. We rejected it for the same reason as [ADR-0001](./0001-sanitising-happens-outside-claudes-read-access.md): date arithmetic that must be exactly right every time (fortnightly cadence, month-end clamping) is a poor fit for an LLM re-deriving it from a sentence on every run, and a structured schedule is also easier to edit correctly in Excel than free text.
