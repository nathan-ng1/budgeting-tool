import logging
from collections.abc import Mapping

from categorisation import config
from categorisation.interface import Categoriser

logger = logging.getLogger(__name__)

BACKENDS = ("claude", "codex", "openai-compatible")


def connect(env: Mapping[str, str] | None = None) -> Categoriser:
    """Build the Categoriser named by CATEGORISER_BACKEND.

    `env` is the configuration to read it from; when it isn't given, the
    ambient one (a repo-root `.env` under the real environment) is loaded. Pass
    it explicitly to choose a backend without touching the process environment.
    """
    if env is None:
        env = config.load()

    backend = env.get("CATEGORISER_BACKEND")
    logger.info("Using categorisation backend: %s", backend)

    if backend == "claude":
        from categorisation import claude_backend

        return claude_backend.connect()
    if backend == "codex":
        from categorisation import codex_backend

        return codex_backend.connect()
    if backend == "openai-compatible":
        from categorisation import openai_compatible_backend

        return openai_compatible_backend.connect(env)

    raise ValueError(
        f"CATEGORISER_BACKEND is {backend!r} - set it to one of {BACKENDS} in .env"
    )
