"""Where categorisation's configuration comes from - see Issue #30.

Reading configuration is separated from acting on it so that a caller (a test,
most of all) can supply settings directly instead of arranging a `.env` file
and process environment to suit. `load()` deliberately does not mutate
`os.environ`, which is what made the old `load_dotenv`-inside-`connect()`
arrangement impossible to test around: a test could clear a variable and have
it reappear from the repo's own `.env` mid-call.
"""

import os
from collections.abc import Mapping
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load() -> Mapping[str, str]:
    """The configured environment: a repo-root `.env` under the real process
    environment, which wins - the same precedence `load_dotenv` applies, minus
    the global side effect."""
    from dotenv import dotenv_values

    return {**dotenv_values(REPO_ROOT / ".env"), **os.environ}
