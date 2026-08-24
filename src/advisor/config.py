"""Where Advisor configuration comes from - mirrors categorisation.config
exactly (Issue #65), kept as its own copy rather than a shared import so
ADVISOR_BACKEND stays a genuinely independent setting from
CATEGORISER_BACKEND (ADR-0014), not two names for one config module.
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
