import logging
from collections.abc import Mapping

from advisor import config
from advisor.interface import Advisor

logger = logging.getLogger(__name__)

BACKENDS = ("claude", "codex", "openai-compatible")


def connect(env: Mapping[str, str] | None = None) -> Advisor:
    """Build the Advisor named by ADVISOR_BACKEND - mirrors
    categorisation.factory.connect exactly.

    `env` is the configuration to read it from; when it isn't given, the
    ambient one (a repo-root `.env` under the real environment) is loaded.
    Pass it explicitly to choose a backend without touching the process
    environment.
    """
    if env is None:
        env = config.load()

    backend = env.get("ADVISOR_BACKEND")
    logger.info("Using advisor backend: %s", backend)

    if backend == "claude":
        from advisor import claude_backend

        return claude_backend.connect()
    if backend == "codex":
        from advisor import codex_backend

        return codex_backend.connect()
    if backend == "openai-compatible":
        from advisor import openai_compatible_backend

        return openai_compatible_backend.connect(env)

    raise ValueError(
        f"ADVISOR_BACKEND is {backend!r} - set it to one of {BACKENDS} in .env"
    )
