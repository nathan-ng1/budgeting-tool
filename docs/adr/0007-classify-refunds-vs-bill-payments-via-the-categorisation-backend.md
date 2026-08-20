# Classify positive-Amount rows as Bill Payment vs Refund via the categorisation backend

Previously every positive-Amount row on a card Statement Export (the old blanket "Payments & Refunds" term) was dropped unconditionally — bill payments and genuine refunds were indistinguishable and neither was tracked. The Dashboard's Real Income stat now needs refunds counted as Income, so we extended the categorisation backend's job (already a per-transaction judgement call, per [ADR-0004](./0004-categorisation-backend-is-pluggable-and-scripted.md)) to also classify positive-Amount rows as Bill Payment (still dropped) or Refund (written as Type Income, Category Refund), with `needs_review` as the fallback for ambiguous cases — rather than a hand-coded, issuer-specific pattern rule.

## Consequences

- The categorisation backend's structured-output schema (`src/categorisation/prompt.py`) grows a new classification axis for positive-Amount rows; all three backends (`claude_backend.py`, `codex_backend.py`, `openai_compatible_backend.py`) need to handle it.
- No real Refund has been observed in historical data yet — this is unverified against a live example until one actually occurs.
